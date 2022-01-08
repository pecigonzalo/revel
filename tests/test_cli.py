# import typer
from typer.testing import CliRunner

from revel import cli

runner = CliRunner()


def test_shows_version():
    result = runner.invoke(
        app=cli.app,
        args=["--version"],
    )

    assert result.exit_code == 0, result.stderr


def test_create_default():
    result = runner.invoke(
        app=cli.app,
        args=["create"],
    )

    assert result.exit_code == 0, result.stderr


def test_delete_default():
    result = runner.invoke(
        app=cli.app,
        args=["delete"],
    )

    assert result.exit_code == 0, result.stderr


def test_start_default():
    result = runner.invoke(
        app=cli.app,
        args=["start"],
    )

    assert result.exit_code == 0, result.stderr


def test_stop_default():
    result = runner.invoke(
        app=cli.app,
        args=["stop"],
    )

    assert result.exit_code == 0, result.stderr
