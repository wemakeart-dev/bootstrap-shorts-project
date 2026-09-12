from pathlib import Path

from bootstrap_shorts.config import ResolvedConfig
from bootstrap_shorts.filesystem import as_ae_path
from bootstrap_shorts.pipeline import run_bootstrap


def _config(tmp_path: Path, name: str = "client-short-01") -> ResolvedConfig:
    templates = tmp_path / "templates"
    projects = tmp_path / "projects"
    templates.mkdir()
    projects.mkdir()
    main = templates / "portrait-short-form.aep"
    preprocess = templates / "portrait-short-form-pre-process.aep"
    footage_dir = tmp_path / "clips"
    footage_dir.mkdir()
    clip = footage_dir / "clip-a.mov"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    clip.write_bytes(b"clip")
    return ResolvedConfig(
        name=name,
        projects_dir=projects,
        project_dir=projects / name,
        raw_footage_dir=footage_dir,
        raw_footage=[clip],
        main_template=main,
        preprocess_template=preprocess,
        after_effects_exe=None,
        main_import_folder="01-footage",
        preprocess_import_folder="footage",
        force=False,
    )


def test_run_bootstrap_prepares_files_and_invokes_ae(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "bootstrap_shorts.pipeline.resolve_afterfx",
        lambda _explicit: Path("C:/AfterFX.exe"),
    )

    def fake_job(afterfx, job_file, result_file, **kwargs):
        captured["afterfx"] = afterfx
        captured["job"] = job_file.read_text(encoding="utf-8")
        captured["result"] = result_file
        return {
            "ok": True,
            "imported_main": ["clip-a.mov"],
            "imported_preprocess": ["clip-a.mov"],
            "relinked": ["logo.png"],
            "warnings": ["demo warning"],
        }

    monkeypatch.setattr("bootstrap_shorts.pipeline.run_after_effects_job", fake_job)

    result = run_bootstrap(config)

    copied = config.project_dir / "(Footage)" / "01-footage" / "clip-a.mov"
    job = config.project_dir / ".bootstrap" / "job.json"
    assert copied.is_file()
    assert copied.read_bytes() == b"clip"
    assert job.is_file()
    assert captured["afterfx"] == Path("C:/AfterFX.exe")
    assert captured["result"] == config.project_dir / ".bootstrap" / "result.json"
    assert as_ae_path(copied) in str(captured["job"])
    assert result["ok"] is True
    assert result["relinked"] == ["logo.png"]
