"""Command-line entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from bootstrap_shorts.ae_bridge import DEFAULT_TIMEOUT_SECONDS
from bootstrap_shorts.config import assign_project_name, load_config
from bootstrap_shorts.errors import BootstrapError
from bootstrap_shorts.pipeline import run_bootstrap
from bootstrap_shorts.project_name import prompt_project_name, require_project_name
from bootstrap_shorts.select_footage import select_raw_footage

app = typer.Typer(rich_markup_mode="rich", add_completion=False)


@app.command()
def main(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to the YAML config file."),
    ] = Path("config.yaml"),
    name: Annotated[
        str | None,
        typer.Option(
            "--name",
            help="Project name (skips the name prompt). Lowercased; spaces become hyphens.",
        ),
    ] = None,
    raw_footage: Annotated[
        Path | None,
        typer.Option("--raw-footage", help="Override the raw footage root directory."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing project directory."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Process every .mov file in the footage root directory without prompting.",
        ),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Seconds to wait for After Effects to finish."),
    ] = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Bootstrap a new After Effects shorts project from templates."""
    console = Console()
    try:
        resolved = load_config(
            config,
            raw_footage=raw_footage,
            force=force,
        )
        selected = select_raw_footage(
            resolved.raw_footage_dir,
            assume_yes=yes,
            console=console,
        )
        resolved = resolved.model_copy(update={"raw_footage": selected})
        if name is None:
            slug = prompt_project_name(console)
        else:
            slug = require_project_name(name)
            console.print(f"Using project name: [bold]{slug}[/bold]")
        resolved = assign_project_name(resolved, slug)
        run_bootstrap(resolved, timeout=timeout, console=console)
    except BootstrapError as exc:
        Console(stderr=True).print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
