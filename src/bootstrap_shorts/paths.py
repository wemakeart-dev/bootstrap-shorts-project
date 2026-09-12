"""Resolve bundled resources and user files for source and frozen runs."""

from __future__ import annotations

import sys
from pathlib import Path

CONFIG_FILENAME = "config.yaml"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if not isinstance(meipass, str) or not meipass:
            raise RuntimeError("Frozen executable is missing sys._MEIPASS")
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def user_files_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def ae_scripts_dir() -> Path:
    return resource_root() / "scripts" / "ae"


def default_config_path() -> Path:
    return user_files_dir() / CONFIG_FILENAME
