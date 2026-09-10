from pathlib import Path

import pytest
import yaml

from bootstrap_shorts.config import (
    assign_project_name,
    discover_mov_files,
    load_config,
    parse_raw_config,
    resolve_config,
)
from bootstrap_shorts.errors import ConfigError, ProjectExistsError


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _layout(tmp_path: Path) -> dict[str, Path]:
    main_dir = tmp_path / "templates" / "portrait-short-form"
    preprocess_dir = tmp_path / "templates" / "portrait-short-form-pre-process"
    projects = tmp_path / "projects"
    footage = tmp_path / "clips"
    main_dir.mkdir(parents=True)
    preprocess_dir.mkdir(parents=True)
    projects.mkdir()
    footage.mkdir()
    main = main_dir / "portrait-short-form.aep"
    preprocess = preprocess_dir / "portrait-short-form-pre-process.aep"
    clip = footage / "clip-a.mov"
    other = footage / "notes.txt"
    ignored = footage / "clip-b.mp4"
    main.write_bytes(b"aep")
    preprocess.write_bytes(b"aep")
    clip.write_bytes(b"mov")
    other.write_bytes(b"txt")
    ignored.write_bytes(b"mp4")
    return {
        "main_dir": main_dir,
        "preprocess_dir": preprocess_dir,
        "projects": projects,
        "footage": footage,
        "clip": clip,
        "main": main,
        "preprocess": preprocess,
    }


def _templates(layout: dict[str, Path]) -> dict[str, str]:
    return {
        "main": str(layout["main_dir"]),
        "pre_process": str(layout["preprocess_dir"]),
    }


def _payload(layout: dict[str, Path], **overrides: object) -> dict:
    data: dict = {
        "templates": _templates(layout),
        "raw_footage": str(layout["footage"]),
        "projects": str(layout["projects"]),
    }
    data.update(overrides)
    return data


def test_load_config_resolves_paths(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    config_path = _write_config(tmp_path, _payload(layout))

    resolved = load_config(config_path)

    assert resolved.name == ""
    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()
    assert resolved.raw_footage_dir == layout["footage"].resolve()
    assert resolved.raw_footage == []
    assert resolved.project_dir == layout["projects"].resolve()
    assert resolved.main_import_folder == "01-footage"
    assert resolved.preprocess_import_folder == "footage"


def test_relative_paths_resolve_against_config_dir(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    nested = tmp_path / "cfg"
    nested.mkdir()
    config_path = _write_config(
        nested,
        {
            "templates": {
                "main": "../templates/portrait-short-form",
                "pre_process": "../templates/portrait-short-form-pre-process",
            },
            "raw_footage": "../clips",
            "projects": "../projects",
        },
    )

    resolved = load_config(config_path)

    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()
    assert resolved.raw_footage_dir == layout["footage"].resolve()
    assert resolved.raw_footage == []


def test_template_file_paths_are_accepted(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        {
            "templates": {
                "main": str(layout["main"]),
                "pre_process": str(layout["preprocess"]),
            },
            "raw_footage": str(layout["footage"]),
            "projects": str(layout["projects"]),
        }
    )

    resolved = resolve_config(raw, config_dir=tmp_path)
    assert resolved.main_template == layout["main"].resolve()
    assert resolved.preprocess_template == layout["preprocess"].resolve()


def test_cli_raw_footage_override_wins(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    override = tmp_path / "other-clips"
    override.mkdir()
    extra = override / "override.mov"
    extra.write_bytes(b"mov")
    config_path = _write_config(tmp_path, _payload(layout))

    resolved = load_config(config_path, raw_footage=override)

    assert resolved.raw_footage_dir == override.resolve()
    assert resolved.raw_footage == []


def test_discover_mov_skips_non_mov(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    hidden = layout["footage"] / ".hidden.mov"
    hidden.write_bytes(b"mov")
    found = discover_mov_files(layout["footage"])
    assert found == [layout["clip"].resolve()]
    assert hidden not in found


def test_missing_key_is_invalid() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config({"projects": "y", "raw_footage": "clips"})


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ConfigError, match="Invalid config"):
        parse_raw_config(
            {
                "templates": {"main": "a", "pre_process": "b"},
                "projects": "y",
                "raw_footage": "clips",
                "unexpected": True,
            }
        )


def test_name_in_config_is_deprecated() -> None:
    with pytest.raises(ConfigError, match="name is deprecated"):
        parse_raw_config(
            {
                "templates": {"main": "a", "pre_process": "b"},
                "projects": "y",
                "raw_footage": "clips",
                "name": "client-short-01",
            }
        )


def test_missing_template(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    layout["main"].unlink()
    raw = parse_raw_config(_payload(layout))

    with pytest.raises(ConfigError, match="Main template not found"):
        resolve_config(raw, config_dir=tmp_path)


def test_missing_template_directory(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(
        _payload(
            layout,
            templates={
                "main": str(tmp_path / "missing-main"),
                "pre_process": str(layout["preprocess_dir"]),
            },
        )
    )

    with pytest.raises(ConfigError, match="Main template path does not exist"):
        resolve_config(raw, config_dir=tmp_path)


def test_missing_footage_directory(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    raw = parse_raw_config(_payload(layout, raw_footage=str(tmp_path / "missing-clips")))

    with pytest.raises(ConfigError, match="raw_footage directory does not exist"):
        resolve_config(raw, config_dir=tmp_path)


def test_empty_footage_directory_is_valid(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    raw = parse_raw_config(_payload(layout, raw_footage=str(empty)))

    resolved = resolve_config(raw, config_dir=tmp_path)
    assert resolved.raw_footage_dir == empty.resolve()
    assert resolved.raw_footage == []


def test_footage_root_with_only_subdirs_is_valid(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    root = tmp_path / "nested-root"
    nested = root / "session-01"
    nested.mkdir(parents=True)
    clip = nested / "nested.mov"
    clip.write_bytes(b"mov")
    raw = parse_raw_config(_payload(layout, raw_footage=str(root)))

    resolved = resolve_config(raw, config_dir=tmp_path)
    assert resolved.raw_footage_dir == root.resolve()
    assert resolved.raw_footage == []
    assert discover_mov_files(root) == []
    assert discover_mov_files(nested) == [clip.resolve()]


def test_discover_mov_empty_directory(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert discover_mov_files(empty) == []


def test_assign_project_name_rejects_existing_without_force(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    existing = layout["projects"] / "already"
    existing.mkdir()
    raw = parse_raw_config(_payload(layout))
    resolved = resolve_config(raw, config_dir=tmp_path, force=False)

    with pytest.raises(ProjectExistsError, match="already exists"):
        assign_project_name(resolved, "already")


def test_assign_project_name_allowed_with_force(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    (layout["projects"] / "already").mkdir()
    raw = parse_raw_config(_payload(layout))
    resolved = resolve_config(raw, config_dir=tmp_path, force=True)

    bound = assign_project_name(resolved, "already")
    assert bound.force is True
    assert bound.name == "already"
    assert bound.project_dir == (layout["projects"] / "already").resolve()


def test_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Config not found"):
        load_config(tmp_path / "nope.yaml")
