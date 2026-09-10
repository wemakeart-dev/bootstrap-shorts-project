"""Prepare the project directory, copy footage, and write the AE job file."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.errors import ConfigError

DISK_FOOTAGE_CONTAINER = "(Footage)"
BOOTSTRAP_DIR_NAME = ".bootstrap"
JOB_FILENAME = "job.json"
RESULT_FILENAME = "result.json"


def as_ae_path(path: Path) -> str:
    """Absolute path using forward slashes, which ExtendScript accepts on Windows."""
    return path.resolve().as_posix()


def disk_footage_dir(project_dir: Path, folder_name: str | None = None) -> Path:
    name = folder_name or "01-footage"
    return project_dir / DISK_FOOTAGE_CONTAINER / name


def bootstrap_dir(project_dir: Path) -> Path:
    return project_dir / BOOTSTRAP_DIR_NAME


def job_path(project_dir: Path) -> Path:
    return bootstrap_dir(project_dir) / JOB_FILENAME


def result_path(project_dir: Path) -> Path:
    return bootstrap_dir(project_dir) / RESULT_FILENAME


def prepare_project_dir(project_dir: Path, *, force: bool) -> None:
    if project_dir.exists() and force:
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=False)
    bootstrap_dir(project_dir).mkdir()


def _copy_one(source: Path, dest_dir: Path, seen_names: set[str]) -> Path:
    if source.name in seen_names:
        raise ConfigError(
            f"Duplicate raw footage filename: {source.name}. "
            "Rename one of the files so each clip is unique."
        )
    seen_names.add(source.name)
    destination = dest_dir / source.name
    shutil.copy2(source, destination)
    return destination.resolve()


def copy_raw_footage(
    sources: list[Path],
    dest_dir: Path,
    *,
    console: Console | None = None,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    seen_names: set[str] = set()
    if console is None:
        for source in sources:
            copied.append(_copy_one(source, dest_dir, seen_names))
        return copied

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Copying footage…", total=len(sources))
        for source in sources:
            copied.append(_copy_one(source, dest_dir, seen_names))
            progress.advance(task_id)
    return copied


def build_job_payload(config: ResolvedConfig, import_files: list[Path]) -> dict[str, Any]:
    root = config.project_dir
    return {
        "project_root": as_ae_path(root),
        "main_template": as_ae_path(config.main_template),
        "preprocess_template": as_ae_path(config.preprocess_template),
        "main_save_as": as_ae_path(root / f"{config.name}.aep"),
        "preprocess_save_as": as_ae_path(root / f"{config.name}-pre-process.aep"),
        "import_files": [as_ae_path(path) for path in import_files],
        "main_import_folder": config.main_import_folder,
        "preprocess_import_folder": config.preprocess_import_folder,
        "collect_existing": True,
        "result_path": as_ae_path(result_path(root)),
    }


def write_job_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_result_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
