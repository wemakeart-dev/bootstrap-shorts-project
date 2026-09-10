"""Launch After Effects and wait for the ExtendScript job result."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from bootstrap_shorts.errors import AfterEffectsJobError
from bootstrap_shorts.filesystem import as_ae_path, read_result_json

LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600.0
POLL_INTERVAL_SECONDS = 0.5


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_job_jsx_path() -> Path:
    path = repo_root() / "scripts" / "ae" / "run_job.jsx"
    if not path.is_file():
        raise AfterEffectsJobError(f"Missing ExtendScript runner: {path}")
    return path


def _escape_ae_string(value: str) -> str:
    return value.replace("\\", "/").replace("'", "\\'")


def build_script_arg(job_file: Path, run_job_jsx: Path) -> str:
    job = _escape_ae_string(as_ae_path(job_file))
    jsx = _escape_ae_string(as_ae_path(run_job_jsx))
    return f"var BOOTSTRAP_JOB_PATH='{job}'; $.evalFile('{jsx}');"


def wait_for_result(
    result_file: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    process: subprocess.Popen[bytes] | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result_file.is_file() and result_file.stat().st_size > 0:
            try:
                payload = read_result_json(result_file)
            except (OSError, json.JSONDecodeError):
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            if "ok" in payload:
                return payload
        time.sleep(POLL_INTERVAL_SECONDS)

    extra = ""
    if process is not None and process.poll() is not None:
        extra = f" AfterFX process exited with code {process.returncode}."
    raise AfterEffectsJobError(
        f"Timed out after {timeout:.0f}s waiting for After Effects result "
        f"at {result_file}.{extra} "
        "Confirm After Effects is installed and that "
        "'Allow Scripts to Write Files and Access Network' is enabled."
    )


def launch_after_effects(
    afterfx_exe: Path,
    job_file: Path,
    run_job_jsx: Path,
) -> subprocess.Popen[bytes]:
    script = build_script_arg(job_file, run_job_jsx)
    command = [str(afterfx_exe), "-s", script]
    LOGGER.debug("Launching After Effects: %s -s <job>", afterfx_exe)
    LOGGER.debug("ExtendScript command: %s", script)
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_after_effects_job(
    afterfx_exe: Path,
    job_file: Path,
    result_file: Path,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    run_job_jsx: Path | None = None,
    console: Console | None = None,
) -> dict[str, Any]:
    jsx = run_job_jsx or run_job_jsx_path()
    if result_file.exists():
        result_file.unlink()

    process = launch_after_effects(afterfx_exe, job_file, jsx)
    try:
        if console is not None:
            with console.status("Waiting for After Effects…"):
                payload = wait_for_result(result_file, timeout=timeout, process=process)
        else:
            payload = wait_for_result(result_file, timeout=timeout, process=process)
    except AfterEffectsJobError:
        if process.poll() is None:
            message = "After Effects is still running; leaving it open."
            if console is not None:
                console.print(f"[yellow]{message}[/yellow]")
            else:
                LOGGER.warning("%s", message)
        raise

    if not payload.get("ok"):
        errors = payload.get("errors") or ["After Effects reported a failure"]
        detail = "; ".join(str(item) for item in errors)
        raise AfterEffectsJobError(f"After Effects job failed: {detail}")
    return payload
