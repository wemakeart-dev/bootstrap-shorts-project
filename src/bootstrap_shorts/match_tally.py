"""Apply timestamps.txt to the currently open After Effects project."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console

from bootstrap_shorts.ae_bridge import (
    DEFAULT_TIMEOUT_SECONDS,
    run_after_effects_job,
    run_match_tally_jsx_path,
)
from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.detect_ae import resolve_afterfx
from bootstrap_shorts.filesystem import as_ae_path, write_job_json
from bootstrap_shorts.timestamps import (
    TallyEvent,
    default_timestamps_path,
    load_timestamps,
)


def build_match_tally_job_payload(
    events: list[TallyEvent],
    result_file: Path,
) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: event.sort_key)
    return {
        "action": "match_tally",
        "timestamps": [
            {"timecode": event.timecode, "tally": event.tally} for event in ordered
        ],
        "result_path": as_ae_path(result_file),
    }


def run_match_tally(
    config: ResolvedConfig,
    *,
    timestamps_file: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    console: Console | None = None,
) -> dict[str, Any]:
    out = console or Console()
    path = timestamps_file or default_timestamps_path()
    events = load_timestamps(path)
    out.print(f"Read {len(events)} timestamp(s) from {path.resolve()}")

    afterfx = resolve_afterfx(config.after_effects_exe)
    out.print(f"Using After Effects at {afterfx}")

    with tempfile.TemporaryDirectory(prefix="bootstrap-shorts-tally-") as tmp:
        tmp_dir = Path(tmp)
        job_file = tmp_dir / "job.json"
        result_file = tmp_dir / "result.json"
        payload = build_match_tally_job_payload(events, result_file)
        written_job = write_job_json(job_file, payload)
        out.print(f"Wrote After Effects job {written_job}")

        result = run_after_effects_job(
            afterfx,
            written_job,
            result_file,
            timeout=timeout,
            run_job_jsx=run_match_tally_jsx_path(),
            console=out,
        )

    for warning in result.get("warnings") or []:
        out.print(f"[yellow]{warning}[/yellow]")

    applied = result.get("applied") or {}
    air = int(applied.get("air") or 0)
    ground = int(applied.get("ground") or 0)
    naval = int(applied.get("naval") or 0)
    out.print(
        f"[green]Applied match tally:[/green] {air} air, {ground} ground, {naval} naval"
    )
    return result
