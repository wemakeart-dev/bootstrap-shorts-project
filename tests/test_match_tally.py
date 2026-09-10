from pathlib import Path

import pytest

from bootstrap_shorts.ae_bridge import run_match_tally_jsx_path
from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.errors import TimestampError
from bootstrap_shorts.filesystem import as_ae_path
from bootstrap_shorts.match_tally import build_match_tally_job_payload, run_match_tally
from bootstrap_shorts.timestamps import parse_timestamps_text


def _config(tmp_path: Path) -> ResolvedConfig:
    templates = tmp_path / "templates"
    projects = tmp_path / "projects"
    footage_dir = tmp_path / "clips"
    templates.mkdir()
    projects.mkdir()
    footage_dir.mkdir()
    main = templates / "portrait-short-form.aep"
    preprocess = templates / "portrait-short-form-pre-process.aep"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    return ResolvedConfig(
        name="",
        projects_dir=projects,
        project_dir=projects,
        raw_footage_dir=footage_dir,
        raw_footage=[],
        main_template=main,
        preprocess_template=preprocess,
        after_effects_exe=None,
        main_import_folder="01-footage",
        preprocess_import_folder="footage",
        force=False,
    )


def test_match_tally_runner_path() -> None:
    path = run_match_tally_jsx_path()
    assert path.name == "run_match_tally.jsx"
    assert path.is_file()


def test_job_payload_shape_and_chronological_order(tmp_path: Path) -> None:
    events = parse_timestamps_text("0:01:00:00 - Air\n0:00:01:00\n0:00:02:00 - Naval\n")
    result_file = tmp_path / "result.json"

    payload = build_match_tally_job_payload(events, result_file)

    assert payload["action"] == "match_tally"
    assert payload["timestamps"] == [
        {"timecode": "0:00:01:00", "tally": "ground"},
        {"timecode": "0:00:02:00", "tally": "naval"},
        {"timecode": "0:01:00:00", "tally": "air"},
    ]
    assert payload["result_path"] == as_ae_path(result_file)
    assert "/" in payload["result_path"]
    assert "\\" not in payload["result_path"]


def test_run_match_tally_missing_file_does_not_launch_ae(
    tmp_path: Path, monkeypatch
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(
        "bootstrap_shorts.match_tally.resolve_afterfx",
        lambda _explicit: launched.append("afterfx") or Path("C:/AfterFX.exe"),
    )
    monkeypatch.setattr(
        "bootstrap_shorts.match_tally.run_after_effects_job",
        lambda *_args, **_kwargs: launched.append("job") or {"ok": True},
    )

    with pytest.raises(TimestampError, match="Timestamps file not found"):
        run_match_tally(_config(tmp_path), timestamps_file=tmp_path / "timestamps.txt")

    assert launched == []


def test_run_match_tally_sends_job_to_tally_runner(
    tmp_path: Path, monkeypatch
) -> None:
    timestamps = tmp_path / "timestamps.txt"
    timestamps.write_text("0:00:01:00\n0:00:02:00 - Air\n", encoding="utf-8")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bootstrap_shorts.match_tally.resolve_afterfx",
        lambda _explicit: Path("C:/AfterFX.exe"),
    )

    def fake_job(
        afterfx_exe: Path,
        job_file: Path,
        result_file: Path,
        **kwargs,
    ) -> dict[str, object]:
        captured["afterfx"] = afterfx_exe
        captured["job"] = job_file.read_text(encoding="utf-8")
        captured["jsx"] = kwargs.get("run_job_jsx")
        return {
            "ok": True,
            "applied": {"air": 1, "ground": 1, "naval": 0},
            "warnings": ["demo warning"],
        }

    monkeypatch.setattr("bootstrap_shorts.match_tally.run_after_effects_job", fake_job)

    result = run_match_tally(_config(tmp_path), timestamps_file=timestamps)

    assert result["applied"] == {"air": 1, "ground": 1, "naval": 0}
    assert captured["afterfx"] == Path("C:/AfterFX.exe")
    assert '"action": "match_tally"' in str(captured["job"])
    assert Path(str(captured["jsx"])).name == "run_match_tally.jsx"
