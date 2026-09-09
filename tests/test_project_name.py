import pytest
from rich.console import Console

from bootstrap_shorts.errors import ConfigError
from bootstrap_shorts.project_name import (
    normalize_project_name,
    prompt_project_name,
    require_project_name,
)


def _console() -> Console:
    return Console(record=True, color_system=None, force_terminal=False, width=80)


def test_normalize_project_name_examples() -> None:
    assert normalize_project_name("Client Short 01") == "client-short-01"
    assert normalize_project_name("client-short-01") == "client-short-01"
    assert normalize_project_name("  Client   Short--01  ") == "client-short-01"


def test_normalize_project_name_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_project_name("   ")
    with pytest.raises(ValueError, match="letters, digits"):
        normalize_project_name("My_Project")
    with pytest.raises(ValueError, match="letters, digits"):
        normalize_project_name("café")
    with pytest.raises(ValueError, match="letters, digits"):
        normalize_project_name("foo/bar")
    with pytest.raises(ValueError, match="must not be empty"):
        normalize_project_name("---")


def test_require_project_name_wraps_config_error() -> None:
    assert require_project_name("Other Short") == "other-short"
    with pytest.raises(ConfigError, match="letters, digits"):
        require_project_name("bad_name")


def test_prompt_project_name_retries_then_accepts() -> None:
    answers = iter(["My_Project", "Client Short 01"])
    console = _console()

    slug = prompt_project_name(console, prompt=lambda *_args, **_kwargs: next(answers))

    assert slug == "client-short-01"
    text = console.export_text()
    assert "may only contain letters, digits, spaces, and hyphens" in text
    assert "Using project name: client-short-01" in text
