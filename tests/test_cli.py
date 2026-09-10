from typer.testing import CliRunner

from bootstrap_shorts.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--config" in result.stdout
    assert "--raw-footage" in result.stdout
    assert "--force" in result.stdout
    assert "--yes" in result.stdout
    assert "--name" in result.stdout
