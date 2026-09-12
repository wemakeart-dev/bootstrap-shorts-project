"""Parse the universal timestamps.txt used by --match-tally."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bootstrap_shorts.errors import TimestampError
from bootstrap_shorts.paths import user_files_dir

TIMESTAMPS_FILENAME = "timestamps.txt"
DEFAULT_TALLY = "ground"
TallyName = Literal["air", "ground", "naval"]
TALLY_LABELS: dict[str, TallyName] = {
    "air": "air",
    "ground": "ground",
    "naval": "naval",
}

_TIMECODE_RE = re.compile(
    r"^(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2}):(?P<frames>\d{2})$"
)
_LINE_RE = re.compile(
    r"^(?P<timecode>\d+:\d{2}:\d{2}:\d{2})(?:\s*-\s*(?P<label>.*))?$"
)


@dataclass(frozen=True)
class TallyEvent:
    timecode: str
    tally: TallyName
    hours: int
    minutes: int
    seconds: int
    frames: int

    @property
    def sort_key(self) -> tuple[int, int, int, int]:
        return (self.hours, self.minutes, self.seconds, self.frames)


def default_timestamps_path() -> Path:
    return user_files_dir() / TIMESTAMPS_FILENAME


def _parse_timecode(timecode: str, *, source: str, line_no: int) -> tuple[int, int, int, int]:
    match = _TIMECODE_RE.fullmatch(timecode)
    if not match:
        raise TimestampError(f"{source}:{line_no}: invalid timecode: {timecode}")
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    frames = int(match.group("frames"))
    if minutes > 59 or seconds > 59:
        raise TimestampError(
            f"{source}:{line_no}: invalid timecode (minutes and seconds must be 00-59): {timecode}"
        )
    return hours, minutes, seconds, frames


def _parse_label(label: str | None, *, source: str, line_no: int) -> TallyName:
    if label is None:
        return DEFAULT_TALLY
    key = label.strip().lower()
    if not key:
        raise TimestampError(f"{source}:{line_no}: missing tally identifier after '-'")
    tally = TALLY_LABELS.get(key)
    if tally is None:
        raise TimestampError(
            f"{source}:{line_no}: unknown tally identifier {label.strip()!r} "
            "(use Air, Ground, or Naval)"
        )
    return tally


def parse_timestamps_text(text: str, *, source: str = TIMESTAMPS_FILENAME) -> list[TallyEvent]:
    events: list[TallyEvent] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        match = _LINE_RE.fullmatch(line)
        if not match:
            raise TimestampError(f"{source}:{line_no}: invalid timestamp line: {raw}")
        timecode = match.group("timecode")
        hours, minutes, seconds, frames = _parse_timecode(
            timecode, source=source, line_no=line_no
        )
        tally = _parse_label(match.group("label"), source=source, line_no=line_no)
        events.append(
            TallyEvent(
                timecode=timecode,
                tally=tally,
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                frames=frames,
            )
        )
    return events


def load_timestamps(path: Path) -> list[TallyEvent]:
    if not path.is_file():
        raise TimestampError(f"Timestamps file not found: {path}")
    return parse_timestamps_text(path.read_text(encoding="utf-8"), source=str(path))
