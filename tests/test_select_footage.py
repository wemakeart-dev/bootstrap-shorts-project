from pathlib import Path

import pytest
from rich.console import Console

from bootstrap_shorts.errors import ConfigError, SelectionAborted
from bootstrap_shorts.select_footage import (
    build_listing_table,
    format_size,
    is_within_root,
    list_browse_entries,
    parse_browse_input,
    parse_selection,
    resolve_enter,
    resolve_up,
    select_raw_footage,
)


def _console() -> Console:
    return Console(record=True, color_system=None, force_terminal=False, width=80)


def _tree(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "footage"
    session = root / "session-01"
    other = root / "session-02"
    takes = session / "takes-a"
    session.mkdir(parents=True)
    other.mkdir()
    takes.mkdir()
    root_clip = root / "root.mov"
    root_clip.write_bytes(b"r" * 10)
    (root / "notes.txt").write_bytes(b"txt")
    (root / "clip.mp4").write_bytes(b"mp4")
    (root / ".hidden").mkdir()
    (root / ".skip.mov").write_bytes(b"hidden")
    first = session / "a.mov"
    second = session / "b.mov"
    first.write_bytes(b"a" * 20)
    second.write_bytes(b"b" * 30)
    (takes / "deep.mov").write_bytes(b"deep")
    return {
        "root": root,
        "session": session,
        "other": other,
        "takes": takes,
        "root_clip": root_clip,
        "first": first,
        "second": second,
    }


def test_format_size() -> None:
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB"
    assert format_size(1024 * 1024) == "1.0 MB"


def test_parse_selection_all_aliases() -> None:
    assert parse_selection("", 3) == [0, 1, 2]
    assert parse_selection("all", 3) == [0, 1, 2]
    assert parse_selection("A", 3) == [0, 1, 2]
    assert parse_selection("*", 3) == [0, 1, 2]


def test_parse_selection_numbers_and_ranges() -> None:
    assert parse_selection("1,3", 4) == [0, 2]
    assert parse_selection("1-3", 4) == [0, 1, 2]
    assert parse_selection("2-3,1", 4) == [0, 1, 2]
    assert parse_selection("1 4", 4) == [0, 3]


def test_parse_selection_invalid() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        parse_selection("5", 3)
    with pytest.raises(ValueError, match="Range out of bounds"):
        parse_selection("3-1", 3)
    with pytest.raises(ValueError, match="Invalid selection"):
        parse_selection("foo", 3)


def test_parse_selection_cancel() -> None:
    with pytest.raises(SelectionAborted):
        parse_selection("q", 3)


def test_list_browse_entries_dirs_first_skips_other_files(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    entries = list_browse_entries(tree["root"])
    names = [entry.path.name for entry in entries]
    assert names == ["session-01", "session-02", "root.mov"]
    assert [entry.is_dir for entry in entries] == [True, True, False]


def test_listing_table_export_text(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    console = _console()
    console.print(build_listing_table(list_browse_entries(tree["root"])))
    text = console.export_text()
    assert "[dir]" in text
    assert "session-01" in text
    assert "root.mov" in text
    assert "notes.txt" not in text
    assert "clip.mp4" not in text


def test_parse_browse_enter_folder(tmp_path: Path) -> None:
    entries = list_browse_entries(_tree(tmp_path)["root"])
    action = parse_browse_input("1", entries)
    assert action.kind == "enter"
    assert action.indexes == (0,)


def test_parse_browse_select_files(tmp_path: Path) -> None:
    entries = list_browse_entries(_tree(tmp_path)["root"])
    action = parse_browse_input("3", entries)
    assert action.kind == "select"
    assert action.indexes == (2,)


def test_parse_browse_all_files_only(tmp_path: Path) -> None:
    entries = list_browse_entries(_tree(tmp_path)["root"])
    action = parse_browse_input("all", entries)
    assert action.kind == "select"
    assert action.indexes == (2,)


def test_parse_browse_up() -> None:
    action = parse_browse_input("..", [])
    assert action.kind == "up"


def test_parse_browse_mix_rejected(tmp_path: Path) -> None:
    entries = list_browse_entries(_tree(tmp_path)["root"])
    with pytest.raises(ValueError, match="Cannot mix folders and files"):
        parse_browse_input("1,3", entries)
    with pytest.raises(ValueError, match="Cannot mix folders and files"):
        parse_browse_input("1-3", entries)


def test_parse_browse_two_folders_rejected(tmp_path: Path) -> None:
    entries = list_browse_entries(_tree(tmp_path)["root"])
    with pytest.raises(ValueError, match="Select one folder to open"):
        parse_browse_input("1,2", entries)


def test_parse_browse_all_without_files(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "only-dir").mkdir()
    with pytest.raises(ValueError, match="No .mov files in this directory"):
        parse_browse_input("all", list_browse_entries(empty))


def test_is_within_root(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    assert is_within_root(tree["root"], tree["root"])
    assert is_within_root(tree["session"], tree["root"])
    assert not is_within_root(tmp_path, tree["root"])


def test_resolve_up_and_enter(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    entered = resolve_enter(tree["root"], tree["root"], tree["session"])
    assert entered == tree["session"].resolve()
    assert resolve_up(entered, tree["root"]) == tree["root"].resolve()
    with pytest.raises(ValueError, match="Already at footage root"):
        resolve_up(tree["root"], tree["root"])


def test_resolve_enter_outside_root(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="outside the footage root"):
        resolve_enter(tree["root"], tree["root"], outside)


def test_select_raw_footage_assume_yes(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    selected = select_raw_footage(tree["root"], assume_yes=True)
    assert selected == [tree["root_clip"].resolve()]


def test_select_raw_footage_assume_yes_no_root_movs(tmp_path: Path) -> None:
    root = tmp_path / "footage"
    nested = root / "session"
    nested.mkdir(parents=True)
    (nested / "clip.mov").write_bytes(b"mov")
    with pytest.raises(ConfigError, match="No .mov files found"):
        select_raw_footage(root, assume_yes=True)


def test_select_raw_footage_prompt_and_confirm(tmp_path: Path) -> None:
    files_dir = tmp_path / "clips"
    files_dir.mkdir()
    files = [files_dir / "a.mov", files_dir / "b.mov", files_dir / "c.mov"]
    for path in files:
        path.write_bytes(b"mov")
    console = _console()

    selected = select_raw_footage(
        files_dir,
        console=console,
        prompt=lambda *_args, **_kwargs: "1,3",
        confirm=lambda *_args, **_kwargs: True,
    )

    text = console.export_text()
    assert selected == [files[0].resolve(), files[2].resolve()]
    assert "a.mov" in text
    assert "Selected 2 file(s)" in text
    assert "Footage root:" in text


def test_select_raw_footage_retry_on_invalid_then_confirm(tmp_path: Path) -> None:
    files_dir = tmp_path / "clips"
    files_dir.mkdir()
    files = [files_dir / "a.mov", files_dir / "b.mov"]
    for path in files:
        path.write_bytes(b"mov")
    answers = iter(["nope", "2"])

    selected = select_raw_footage(
        files_dir,
        console=_console(),
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: True,
    )

    assert selected == [files[1].resolve()]


def test_select_raw_footage_reprompt_when_not_confirmed(tmp_path: Path) -> None:
    files_dir = tmp_path / "clips"
    files_dir.mkdir()
    files = [files_dir / "a.mov", files_dir / "b.mov"]
    for path in files:
        path.write_bytes(b"mov")
    answers = iter(["1", "all"])
    confirms = iter([False, True])

    selected = select_raw_footage(
        files_dir,
        console=_console(),
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: next(confirms),
    )

    assert selected == [path.resolve() for path in files]


def test_select_raw_footage_enter_child_then_select(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    answers = iter(["1", "2,3"])
    console = _console()

    selected = select_raw_footage(
        tree["root"],
        console=console,
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: True,
    )

    assert selected == [tree["first"].resolve(), tree["second"].resolve()]
    text = console.export_text()
    assert "session-01" in text
    assert "a.mov" in text
    assert "deep.mov" not in text


def test_select_raw_footage_up_from_child(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    answers = iter(["1", "..", "3"])
    selected = select_raw_footage(
        tree["root"],
        console=_console(),
        prompt=lambda *_args, **_kwargs: next(answers),
        confirm=lambda *_args, **_kwargs: True,
    )
    assert selected == [tree["root_clip"].resolve()]


def test_select_raw_footage_up_at_root_refused(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    answers = iter(["..", "q"])
    console = _console()
    with pytest.raises(SelectionAborted):
        select_raw_footage(
            tree["root"],
            console=console,
            prompt=lambda *_args, **_kwargs: next(answers),
            confirm=lambda *_args, **_kwargs: True,
        )
    assert "Already at footage root" in console.export_text()


def test_select_raw_footage_cancel(tmp_path: Path) -> None:
    tree = _tree(tmp_path)
    with pytest.raises(SelectionAborted):
        select_raw_footage(
            tree["root"],
            console=_console(),
            prompt=lambda *_args, **_kwargs: "q",
            confirm=lambda *_args, **_kwargs: True,
        )
