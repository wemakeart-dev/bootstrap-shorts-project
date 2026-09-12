import json
from pathlib import Path

import pytest

from bootstrap_shorts.ae_bridge import (
    build_script_arg,
    run_after_effects_job,
    run_job_jsx_path,
    wait_for_result,
)
from bootstrap_shorts.errors import AfterEffectsJobError


def test_build_script_arg_uses_forward_slashes(tmp_path: Path) -> None:
    job = tmp_path / "job.json"
    jsx = tmp_path / "run_job.jsx"
    job.write_text("{}", encoding="utf-8")
    jsx.write_text("//", encoding="utf-8")

    script = build_script_arg(job, jsx)

    assert script.startswith("var BOOTSTRAP_JOB_PATH='")
    assert "$.evalFile('" in script
    assert "\\" not in script
    assert job.resolve().as_posix() in script
    assert jsx.resolve().as_posix() in script


def test_wait_for_result_reads_ok_payload(tmp_path: Path) -> None:
    result = tmp_path / "result.json"
    result.write_text(json.dumps({"ok": True, "errors": []}), encoding="utf-8")

    payload = wait_for_result(result, timeout=1)

    assert payload["ok"] is True


def test_wait_for_result_times_out(tmp_path: Path) -> None:
    with pytest.raises(AfterEffectsJobError, match="Timed out"):
        wait_for_result(tmp_path / "missing.json", timeout=0.2)


def test_run_job_jsx_path_exists() -> None:
    path = run_job_jsx_path()
    assert path.is_file()
    assert path.name == "run_job.jsx"
    assert (path.parent / "lib.jsx").is_file()


class _FakeProcess:
    def poll(self) -> None:
        return None


def test_run_after_effects_job_reads_ok_payload(tmp_path: Path, monkeypatch) -> None:
    job = tmp_path / "job.json"
    result = tmp_path / "result.json"
    jsx = tmp_path / "run_job.jsx"
    job.write_text("{}", encoding="utf-8")
    jsx.write_text("//", encoding="utf-8")

    def fake_launch(*_args, **_kwargs):
        result.write_text(json.dumps({"ok": True, "errors": []}), encoding="utf-8")
        return _FakeProcess()

    monkeypatch.setattr("bootstrap_shorts.ae_bridge.launch_after_effects", fake_launch)

    payload = run_after_effects_job(
        Path("C:/AfterFX.exe"),
        job,
        result,
        timeout=1,
        run_job_jsx=jsx,
    )
    assert payload["ok"] is True


def test_run_after_effects_job_reports_failure(tmp_path: Path, monkeypatch) -> None:
    job = tmp_path / "job.json"
    result = tmp_path / "result.json"
    jsx = tmp_path / "run_job.jsx"
    job.write_text("{}", encoding="utf-8")
    jsx.write_text("//", encoding="utf-8")

    def fake_launch(*_args, **_kwargs):
        result.write_text(
            json.dumps({"ok": False, "errors": ["no project"]}),
            encoding="utf-8",
        )
        return _FakeProcess()

    monkeypatch.setattr("bootstrap_shorts.ae_bridge.launch_after_effects", fake_launch)

    with pytest.raises(AfterEffectsJobError, match="no project"):
        run_after_effects_job(
            Path("C:/AfterFX.exe"),
            job,
            result,
            timeout=1,
            run_job_jsx=jsx,
        )
