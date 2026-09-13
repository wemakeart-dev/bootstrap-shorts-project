import sys
from pathlib import Path

from bootstrap_shorts.paths import (
    ae_scripts_dir,
    default_config_path,
    is_frozen,
    resource_root,
    user_files_dir,
)
from bootstrap_shorts.timestamps import default_timestamps_path


def test_source_resource_root_contains_scripts() -> None:
    root = resource_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "scripts" / "ae" / "run_job.jsx").is_file()
    assert is_frozen() is False


def test_ae_scripts_are_siblings() -> None:
    directory = ae_scripts_dir()
    assert (directory / "run_job.jsx").is_file()
    assert (directory / "run_match_tally.jsx").is_file()
    assert (directory / "lib.jsx").is_file()


def test_source_user_files_dir_is_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.chdir(tmp_path)

    assert user_files_dir() == tmp_path
    assert default_config_path() == tmp_path / "config.yaml"
    assert default_timestamps_path() == tmp_path / "timestamps.txt"


def test_frozen_resource_and_user_dirs(tmp_path: Path, monkeypatch) -> None:
    meipass = tmp_path / "meipass"
    exe = tmp_path / "dist" / "bsp.exe"
    meipass.mkdir()
    (meipass / "scripts" / "ae").mkdir(parents=True)
    exe.parent.mkdir()
    exe.write_bytes(b"mz")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))

    assert is_frozen() is True
    assert resource_root() == meipass
    assert user_files_dir() == exe.parent.resolve()
    assert ae_scripts_dir() == meipass / "scripts" / "ae"
    assert default_config_path() == exe.parent.resolve() / "config.yaml"
    assert default_timestamps_path() == exe.parent.resolve() / "timestamps.txt"
