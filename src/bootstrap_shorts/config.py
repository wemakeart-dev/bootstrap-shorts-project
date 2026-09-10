"""Load and validate the universal YAML config."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from bootstrap_shorts.errors import ConfigError, ProjectExistsError

DEFAULT_MAIN_TEMPLATE = "portrait-short-form.aep"
DEFAULT_PREPROCESS_TEMPLATE = "portrait-short-form-pre-process.aep"
DEFAULT_MAIN_IMPORT_FOLDER = "01-footage"
DEFAULT_PREPROCESS_IMPORT_FOLDER = "footage"
RAW_FOOTAGE_SUFFIX = ".mov"


class TemplatesMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main: str = DEFAULT_MAIN_TEMPLATE
    pre_process: str = DEFAULT_PREPROCESS_TEMPLATE


class TemplatesPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main: Path
    pre_process: Path


class ProjectFolders(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_import: str = DEFAULT_MAIN_IMPORT_FOLDER
    preprocess_import: str = DEFAULT_PREPROCESS_IMPORT_FOLDER


class RawConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    templates: TemplatesPaths
    raw_footage: Path
    projects: Path
    after_effects_exe: Path | None = None
    templates_map: TemplatesMap = Field(default_factory=TemplatesMap)
    project_folders: ProjectFolders = Field(default_factory=ProjectFolders)


class ResolvedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: str
    projects_dir: Path
    project_dir: Path
    raw_footage_dir: Path
    raw_footage: list[Path]
    main_template: Path
    preprocess_template: Path
    after_effects_exe: Path | None
    main_import_folder: str
    preprocess_import_folder: str
    force: bool = False


def _resolve_path(value: Path, base: Path) -> Path:
    path = value.expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def discover_mov_files(directory: Path) -> list[Path]:
    """Collect `.mov` files in `directory` (non-recursive, case-insensitive)."""
    if not directory.is_dir():
        raise ConfigError(f"raw_footage directory does not exist: {directory}")
    files = [
        path.resolve()
        for path in directory.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() == RAW_FOOTAGE_SUFFIX
    ]
    files.sort(key=lambda path: path.name.lower())
    return files


def resolve_template(path: Path, filename: str, label: str) -> Path:
    if path.is_file():
        return path
    if path.is_dir():
        candidate = (path / filename).resolve()
        if candidate.is_file():
            return candidate
        raise ConfigError(f"{label} not found: {candidate}")
    raise ConfigError(f"{label} path does not exist: {path}")


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Config not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a mapping: {path}")
    return data


def parse_raw_config(
    data: dict,
    *,
    raw_footage: Path | None = None,
) -> RawConfig:
    payload = dict(data)
    if "name" in payload:
        raise ConfigError(
            "name is deprecated; enter the project name when prompted, or pass --name"
        )
    if raw_footage is not None:
        payload["raw_footage"] = str(raw_footage)
    try:
        return RawConfig.model_validate(payload)
    except Exception as exc:
        raise ConfigError(f"Invalid config: {exc}") from exc


def resolve_config(
    raw: RawConfig,
    *,
    config_dir: Path,
    force: bool = False,
) -> ResolvedConfig:
    base = config_dir.resolve()
    projects_dir = _resolve_path(raw.projects, base)
    after_effects_exe = (
        _resolve_path(raw.after_effects_exe, base) if raw.after_effects_exe else None
    )

    if not projects_dir.exists():
        raise ConfigError(f"projects directory does not exist: {projects_dir}")
    if not projects_dir.is_dir():
        raise ConfigError(f"projects is not a directory: {projects_dir}")

    main_template = resolve_template(
        _resolve_path(raw.templates.main, base),
        raw.templates_map.main,
        "Main template",
    )
    preprocess_template = resolve_template(
        _resolve_path(raw.templates.pre_process, base),
        raw.templates_map.pre_process,
        "Pre-process template",
    )

    raw_footage_dir = _resolve_path(raw.raw_footage, base)
    if not raw_footage_dir.is_dir():
        raise ConfigError(f"raw_footage directory does not exist: {raw_footage_dir}")

    return ResolvedConfig(
        name="",
        projects_dir=projects_dir,
        project_dir=projects_dir,
        raw_footage_dir=raw_footage_dir,
        raw_footage=[],
        main_template=main_template,
        preprocess_template=preprocess_template,
        after_effects_exe=after_effects_exe,
        main_import_folder=raw.project_folders.main_import,
        preprocess_import_folder=raw.project_folders.preprocess_import,
        force=force,
    )


def assign_project_name(config: ResolvedConfig, name: str) -> ResolvedConfig:
    """Bind a normalized project name and destination directory."""
    project_dir = (config.projects_dir / name).resolve()
    if project_dir.exists() and not config.force:
        raise ProjectExistsError(
            f"Project directory already exists: {project_dir} (use --force to replace it)"
        )
    return config.model_copy(update={"name": name, "project_dir": project_dir})


def load_config(
    path: Path,
    *,
    raw_footage: Path | None = None,
    force: bool = False,
) -> ResolvedConfig:
    data = load_yaml(path)
    raw = parse_raw_config(data, raw_footage=raw_footage)
    return resolve_config(raw, config_dir=path.parent, force=force)
