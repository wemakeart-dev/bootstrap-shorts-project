from pathlib import Path

import pytest

from bootstrap_shorts.errors import TimestampError
from bootstrap_shorts.timestamps import load_timestamps, parse_timestamps_text

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "example-timestamps.txt"


def test_parse_example_timestamps() -> None:
    events = load_timestamps(EXAMPLE)

    assert [event.tally for event in events] == ["ground"] * 9 + ["naval", "ground", "air"]
    assert events[0].timecode == "0:00:02:32"
    assert events[9].timecode == "0:01:06:11"
    assert events[-1].timecode == "0:01:29:51"
    assert sum(1 for event in events if event.tally == "ground") == 10
    assert sum(1 for event in events if event.tally == "naval") == 1
    assert sum(1 for event in events if event.tally == "air") == 1


def test_default_identifier_is_ground() -> None:
    events = parse_timestamps_text("0:00:01:00\n")

    assert len(events) == 1
    assert events[0].tally == "ground"
    assert events[0].timecode == "0:00:01:00"


def test_labels_are_case_insensitive() -> None:
    events = parse_timestamps_text(
        "0:00:01:00 - AIR\n0:00:02:00 - ground\n0:00:03:00 - Naval\n"
    )

    assert [event.tally for event in events] == ["air", "ground", "naval"]


def test_blank_lines_are_ignored() -> None:
    events = parse_timestamps_text("\n0:00:01:00\n\n  \n0:00:02:00 - Air\n")

    assert [event.timecode for event in events] == ["0:00:01:00", "0:00:02:00"]
    assert [event.tally for event in events] == ["ground", "air"]


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(TimestampError, match="unknown tally identifier 'Sea'"):
        parse_timestamps_text("0:00:01:00 - Sea\n", source="timestamps.txt")


def test_malformed_timecode_is_rejected() -> None:
    with pytest.raises(TimestampError, match="invalid timestamp line"):
        parse_timestamps_text("2 seconds\n")


def test_invalid_minutes_are_rejected() -> None:
    with pytest.raises(TimestampError, match="minutes and seconds"):
        parse_timestamps_text("0:61:00:00\n")


def test_missing_label_after_hyphen_is_rejected() -> None:
    with pytest.raises(TimestampError, match="missing tally identifier"):
        parse_timestamps_text("0:00:01:00 -\n")


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "timestamps.txt"
    with pytest.raises(TimestampError, match="Timestamps file not found"):
        load_timestamps(missing)


def test_empty_file_yields_no_events() -> None:
    assert parse_timestamps_text("\n\n") == []
