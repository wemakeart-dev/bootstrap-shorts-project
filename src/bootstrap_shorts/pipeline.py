"""End-to-end bootstrap: prepare files, then drive After Effects."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from bootstrap_shorts.ae_bridge import DEFAULT_TIMEOUT_SECONDS, run_after_effects_job
from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.detect_ae import resolve_afterfx
from bootstrap_shorts.filesystem import (
    build_job_payload,
    copy_raw_footage,
    disk_footage_dir,
    job_path,
    prepare_project_dir,
    result_path,
    write_job_json,
)


def run_bootstrap(
    config: ResolvedConfig,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    console: Console | None = None,
) -> dict[str, Any]:
    out = console or Console()
    root = config.project_dir
    out.print(f"Preparing project directory [bold]{root}[/bold]")
    prepare_project_dir(root, force=config.force)

    footage_dir = disk_footage_dir(root, config.main_import_folder)
    out.print(
        f"Copying {len(config.raw_footage)} .mov file(s) "
        f"from {config.raw_footage_dir} to {footage_dir}"
    )
    imported_files = copy_raw_footage(config.raw_footage, footage_dir, console=out)

    payload = build_job_payload(config, imported_files)
    written_job = write_job_json(job_path(root), payload)
    out.print(f"Wrote After Effects job {written_job}")

    afterfx = resolve_afterfx(config.after_effects_exe)
    out.print(f"Using After Effects at {afterfx}")

    result = run_after_effects_job(
        afterfx,
        written_job,
        result_path(root),
        timeout=timeout,
        console=out,
    )

    for warning in result.get("warnings") or []:
        out.print(f"[yellow]{warning}[/yellow]")

    out.print(
        f"Imported {len(result.get('imported_main') or [])} item(s) into the main project "
        f"and {len(result.get('imported_preprocess') or [])} item(s) into the pre-process project"
    )
    relinked = result.get("relinked") or []
    if relinked:
        out.print(f"Relinked {len(relinked)} existing template footage item(s)")

    out.print(f"[green]Bootstrap complete:[/green] {root}")
    return result
