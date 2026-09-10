"""Errors raised by the bootstrap CLI."""


class BootstrapError(Exception):
    """Base error; the CLI maps this to a non-zero exit."""


class ConfigError(BootstrapError):
    """Config is missing, invalid, or points at missing inputs."""


class ProjectExistsError(BootstrapError):
    """The destination project directory already exists."""


class AfterFXNotFoundError(BootstrapError):
    """AfterFX.exe could not be resolved."""


class AfterEffectsJobError(BootstrapError):
    """After Effects did not complete the job successfully."""


class SelectionAborted(BootstrapError):
    """The user cancelled footage selection."""


class TimestampError(BootstrapError):
    """timestamps.txt is missing or invalid."""
