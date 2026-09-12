from pathlib import Path

import yaml

from bootstrap_shorts.config import parse_raw_config, resolve_config

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "bootstrap-shorts.spec"
EXAMPLE_CONFIG = REPO_ROOT / "config.example.yaml"


def test_spec_bundles_ae_scripts() -> None:
    spec = SPEC_PATH.read_text(encoding="utf-8")
    assert SPEC_PATH.is_file()
    assert "scripts" in spec and "ae" in spec
    assert '"scripts/ae"' in spec or "'scripts/ae'" in spec
    assert "upx=False" in spec
    assert "console=True" in spec
    assert "name=\"bootstrap-shorts\"" in spec or "name='bootstrap-shorts'" in spec


def test_example_config_is_valid_with_stubbed_paths(tmp_path: Path) -> None:
    data = yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    main_dir = tmp_path / "portrait-short-form"
    preprocess_dir = tmp_path / "portrait-short-form-pre-process"
    footage = tmp_path / "raw-footage"
    projects = tmp_path / "projects"
    main_dir.mkdir()
    preprocess_dir.mkdir()
    footage.mkdir()
    projects.mkdir()
    (main_dir / "portrait-short-form.aep").write_bytes(b"aep")
    (preprocess_dir / "portrait-short-form-pre-process.aep").write_bytes(b"aep")

    data["templates"] = {
        "main": str(main_dir),
        "pre_process": str(preprocess_dir),
    }
    data["raw_footage"] = str(footage)
    data["projects"] = str(projects)

    raw = parse_raw_config(data)
    resolved = resolve_config(raw, config_dir=tmp_path)
    assert resolved.main_template == (main_dir / "portrait-short-form.aep").resolve()
    assert resolved.preprocess_template == (
        preprocess_dir / "portrait-short-form-pre-process.aep"
    ).resolve()
    assert resolved.main_import_folder == "01-footage"
    assert resolved.preprocess_import_folder == "footage"
