"""Interactive selection of raw footage files inside a jailed root folder."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.box import SIMPLE
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from bootstrap_shorts.config import RAW_FOOTAGE_SUFFIX, discover_mov_files
from bootstrap_shorts.errors import ConfigError, SelectionAborted

UNITS = ("B", "KB", "MB", "GB", "TB")

BrowseKind = Literal["select", "enter", "up"]


@dataclass(frozen=True)
class BrowseEntry:
    path: Path
    is_dir: bool


@dataclass(frozen=True)
class BrowseAction:
    kind: BrowseKind
    indexes: tuple[int, ...] = ()


def format_size(size: int) -> str:
    value = float(size)
    for unit in UNITS:
        if value < 1024 or unit == UNITS[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def is_within_root(path: Path, root: Path) -> bool:
    resolved = path.resolve()
    root_resolved = root.resolve()
    return resolved == root_resolved or resolved.is_relative_to(root_resolved)


def list_browse_entries(directory: Path) -> list[BrowseEntry]:
    """Child directories first, then `.mov` files. Skip dot-names and other files."""
    dirs: list[BrowseEntry] = []
    files: list[BrowseEntry] = []
    for path in directory.iterdir():
        if path.name.startswith("."):
            continue
        if path.is_dir():
            dirs.append(BrowseEntry(path=path.resolve(), is_dir=True))
        elif path.is_file() and path.suffix.lower() == RAW_FOOTAGE_SUFFIX:
            files.append(BrowseEntry(path=path.resolve(), is_dir=False))
    dirs.sort(key=lambda entry: entry.path.name.lower())
    files.sort(key=lambda entry: entry.path.name.lower())
    return dirs + files


def resolve_enter(cwd: Path, root: Path, child: Path) -> Path:
    candidate = child.resolve()
    if not candidate.is_dir():
        raise ValueError(f"Not a directory: {child.name}")
    if not is_within_root(candidate, root):
        raise ValueError("Cannot navigate outside the footage root")
    return candidate


def resolve_up(cwd: Path, root: Path) -> Path:
    cwd_resolved = cwd.resolve()
    root_resolved = root.resolve()
    if cwd_resolved == root_resolved:
        raise ValueError("Already at footage root")
    parent = cwd_resolved.parent
    if not is_within_root(parent, root_resolved):
        raise ValueError("Cannot navigate outside the footage root")
    return parent


def parse_selection(text: str, count: int) -> list[int]:
    """Parse a selection string into 0-based indexes."""
    cleaned = text.strip().lower()
    if cleaned in {"q", "quit", "cancel"}:
        raise SelectionAborted("Footage selection cancelled")
    if cleaned in {"", "all", "a", "*"}:
        return list(range(count))

    return _parse_numeric_indexes(cleaned, count)


def _parse_numeric_indexes(cleaned: str, count: int) -> list[int]:
    indexes: set[int] = set()
    token = cleaned.replace(" ", ",")
    for part in token.split(","):
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError as exc:
                raise ValueError(f"Invalid range: {part}") from exc
            if start < 1 or end > count or start > end:
                raise ValueError(f"Range out of bounds: {part}")
            indexes.update(range(start - 1, end))
            continue
        try:
            number = int(part)
        except ValueError as exc:
            raise ValueError(f"Invalid selection: {part}") from exc
        if number < 1 or number > count:
            raise ValueError(f"Selection out of bounds: {number}")
        indexes.add(number - 1)

    if not indexes:
        raise ValueError("No files selected")
    return sorted(indexes)


def parse_browse_input(text: str, entries: list[BrowseEntry]) -> BrowseAction:
    """Parse browser input against a mixed folder/file listing."""
    cleaned = text.strip().lower()
    if cleaned in {"q", "quit", "cancel"}:
        raise SelectionAborted("Footage selection cancelled")
    if cleaned == "..":
        return BrowseAction(kind="up")
    if cleaned in {"", "all", "a", "*"}:
        file_indexes = tuple(index for index, entry in enumerate(entries) if not entry.is_dir)
        if not file_indexes:
            raise ValueError("No .mov files in this directory")
        return BrowseAction(kind="select", indexes=file_indexes)

    indexes = _parse_numeric_indexes(cleaned, len(entries))
    folder_indexes = [index for index in indexes if entries[index].is_dir]
    file_indexes = [index for index in indexes if not entries[index].is_dir]
    if folder_indexes and file_indexes:
        raise ValueError("Cannot mix folders and files in one selection")
    if folder_indexes:
        if len(folder_indexes) != 1:
            raise ValueError("Select one folder to open")
        return BrowseAction(kind="enter", indexes=(folder_indexes[0],))
    return BrowseAction(kind="select", indexes=tuple(file_indexes))


def build_listing_table(
    entries: list[BrowseEntry],
    numbers: list[int] | None = None,
) -> Table:
    table = Table(box=SIMPLE, show_edge=False, pad_edge=False, header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Name")
    table.add_column("Size", justify="right", style="dim")

    labels = numbers if numbers is not None else list(range(1, len(entries) + 1))
    for label, entry in zip(labels, entries, strict=True):
        if entry.is_dir:
            name = Text()
            name.append("[dir] ", style="cyan")
            name.append(entry.path.name)
            table.add_row(str(label), name, "")
            continue
        try:
            size = format_size(entry.path.stat().st_size)
        except OSError:
            size = "unknown"
        table.add_row(str(label), entry.path.name, size)
    return table


def _print_browser(
    console: Console,
    *,
    root: Path,
    cwd: Path,
    entries: list[BrowseEntry],
) -> None:
    console.print(f"[dim]Footage root:[/dim] {root}")
    current = "(root)" if cwd.resolve() == root.resolve() else str(cwd)
    console.print(f"[bold]Current:[/bold]      {current}")
    console.print()
    console.print(build_listing_table(entries))
    console.print()
    hint = "Enter file numbers (1,3), ranges (1-3), a folder number to open, all"
    if cwd.resolve() != root.resolve():
        hint += ", .. to go up"
    hint += ", or q to cancel."
    console.print(f"[dim]{hint}[/dim]")


def _print_selected(console: Console, selected: list[BrowseEntry], numbers: list[int]) -> None:
    console.print()
    console.print(f"Selected {len(selected)} file(s):")
    console.print(build_listing_table(selected, numbers))
    console.print()


def select_raw_footage(
    root: Path,
    *,
    assume_yes: bool = False,
    console: Console | None = None,
    prompt: Callable[..., str] | None = None,
    confirm: Callable[..., bool] | None = None,
) -> list[Path]:
    """Browse inside `root`, let the user choose `.mov` files in one folder, and confirm."""
    root = root.resolve()
    if assume_yes:
        files = discover_mov_files(root)
        if not files:
            raise ConfigError(f"No .mov files found in raw_footage directory: {root}")
        return files

    console = console or Console()

    def ask(message: str, default: str = "") -> str:
        if prompt is not None:
            return prompt(message, default=default)
        return Prompt.ask(message, default=default, console=console)

    def confirm_ask(message: str, default: bool = True) -> bool:
        if confirm is not None:
            return confirm(message, default=default)
        return Confirm.ask(message, default=default, console=console)

    cwd = root
    while True:
        entries = list_browse_entries(cwd)
        _print_browser(console, root=root, cwd=cwd, entries=entries)
        raw = ask("Select files or open a folder", default="all")
        try:
            action = parse_browse_input(raw, entries)
        except SelectionAborted:
            raise
        except ValueError as exc:
            console.print(f"[yellow]Invalid selection: {exc}[/yellow]")
            console.print()
            continue

        if action.kind == "up":
            try:
                cwd = resolve_up(cwd, root)
            except ValueError as exc:
                console.print(f"[yellow]{exc}[/yellow]")
                console.print()
            continue

        if action.kind == "enter":
            child = entries[action.indexes[0]].path
            try:
                cwd = resolve_enter(cwd, root, child)
            except ValueError as exc:
                console.print(f"[yellow]{exc}[/yellow]")
                console.print()
            continue

        selected_entries = [entries[index] for index in action.indexes]
        numbers = [index + 1 for index in action.indexes]
        _print_selected(console, selected_entries, numbers)
        if confirm_ask("Process these files?", default=True):
            return [entry.path for entry in selected_entries]
        console.print("[dim]Selection cleared. Choose again.[/dim]")
        console.print()
