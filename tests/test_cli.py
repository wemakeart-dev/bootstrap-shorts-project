from pathlib import Path

import yaml
from typer.testing import CliRunner

from bootstrap_shorts.cli import app

runner = CliRunner()


def _write_valid_config(tmp_path: Path) -> Path:
    main_dir = tmp_path / "templates" / "portrait-short-form"
    preprocess_dir = tmp_path / "templates" / "portrait-short-form-pre-process"
    projects = tmp_path / "projects"
    footage = tmp_path / "clips"
    main_dir.mkdir(parents=True)
    preprocess_dir.mkdir(parents=True)
    projects.mkdir()
    footage.mkdir()
    (main_dir / "portrait-short-form.aep").write_bytes(b"aep")
    (preprocess_dir / "portrait-short-form-pre-process.aep").write_bytes(b"aep")
    path = tmp_path / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "templates": {
                    "main": str(main_dir),
                    "pre_process": str(preprocess_dir),
                },
                "raw_footage": str(footage),
                "projects": str(projects),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--config" in result.stdout
    assert "--raw-footage" in result.stdout
    assert "--force" in result.stdout
    assert "--yes" in result.stdout
    assert "--name" in result.stdout
    assert "--match-tally" in result.stdout


def test_match_tally_missing_timestamps_does_not_launch_ae(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_valid_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    launched: list[str] = []

    def mark_launch(*_args, **_kwargs):
        launched.append("ae")
        raise AssertionError("should not launch After Effects")

    monkeypatch.setattr("bootstrap_shorts.match_tally.run_after_effects_job", mark_launch)
    monkeypatch.setattr(
        "bootstrap_shorts.cli.select_raw_footage",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not browse footage")
        ),
    )

    result = runner.invoke(app, ["--match-tally", "--config", str(config_path)])

    assert result.exit_code == 1
    assert launched == []
    combined = f"{result.stdout or ''}{result.stderr or ''}"
    assert "Timestamps file not found" in combined


def test_match_tally_skips_bootstrap_prompts(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_valid_config(tmp_path)
    (tmp_path / "timestamps.txt").write_text("0:00:01:00\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bootstrap_shorts.cli.select_raw_footage",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not browse footage")
        ),
    )
    monkeypatch.setattr(
        "bootstrap_shorts.cli.prompt_project_name",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not prompt for a project name")
        ),
    )
    monkeypatch.setattr(
        "bootstrap_shorts.match_tally.resolve_afterfx",
        lambda _explicit: Path("C:/AfterFX.exe"),
    )
    monkeypatch.setattr(
        "bootstrap_shorts.match_tally.run_after_effects_job",
        lambda *_args, **_kwargs: {
            "ok": True,
            "applied": {"air": 0, "ground": 1, "naval": 0},
            "warnings": [],
        },
    )

    result = runner.invoke(app, ["--match-tally", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Applied match tally" in result.stdout
    assert "0 air, 1 ground, 0 naval" in result.stdout
