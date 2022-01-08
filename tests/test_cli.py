# import typer
import pytest
from typer.testing import CliRunner

from revel import cli

runner = CliRunner()


def test_shows_version():
    result = runner.invoke(
        app=cli.app,
        args=["--version"],
    )

    assert result.exit_code == 0, result.stderr


@pytest.mark.parametrize("command", ["create", "delete", "start", "stop"])
def test_operate_with_instance_name(command):
    instance_name = "revel1"
    result = runner.invoke(
        app=cli.app,
        args=[command, instance_name],
    )

    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("command", ["create", "delete", "start", "stop"])
def test_operate_with_default(command):
    result = runner.invoke(
        app=cli.app,
        args=[command],
    )

    assert result.exit_code == 0, result.output
