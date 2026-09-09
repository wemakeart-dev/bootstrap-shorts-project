"""Normalize and prompt for the new project folder name."""

from __future__ import annotations

import re
from collections.abc import Callable

from rich.console import Console
from rich.prompt import Prompt

from bootstrap_shorts.errors import ConfigError

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INVALID_CHARS = re.compile(r"[^A-Za-z0-9 -]")


def normalize_project_name(value: str) -> str:
    """Lowercase, turn spaces into hyphens, and require an alphanumeric slug."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("Project name must not be empty")
    if INVALID_CHARS.search(stripped):
        raise ValueError("Project name may only contain letters, digits, spaces, and hyphens")
    slug = re.sub(r" +", "-", stripped.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("Project name must not be empty")
    return slug


def require_project_name(value: str) -> str:
    """Normalize a `--name` override, or raise ConfigError."""
    try:
        return normalize_project_name(value)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


def prompt_project_name(
    console: Console,
    prompt: Callable[..., str] | None = None,
) -> str:
    """Ask for a project name until the input normalizes to a valid slug."""

    def ask(message: str) -> str:
        if prompt is not None:
            return prompt(message)
        return Prompt.ask(message, console=console)

    while True:
        raw = ask("Project name")
        try:
            slug = normalize_project_name(raw)
        except ValueError as exc:
            console.print(f"[yellow]{exc}[/yellow]")
            console.print()
            continue
        console.print(f"Using project name: [bold]{slug}[/bold]")
        return slug
