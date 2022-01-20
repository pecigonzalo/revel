# import pytest
# from pytest_mock import MockerFixture
from typer.testing import CliRunner

# from revel import MachineManager,
from revel import cli

# from revel.machine import Machine

runner = CliRunner()


def test_shows_version():
    result = runner.invoke(
        app=cli.app,
        args=["--version"],
    )

    assert result.exit_code == 0, result.output


def test_shows_help():
    # Explicitly show help
    result = runner.invoke(
        app=cli.app,
        args=["--help"],
    )

    assert result.exit_code == 0, result.output

    # Show help if no command
    result = runner.invoke(
        app=cli.app,
    )

    assert result.exit_code == 0, result.output


# @pytest.mark.parametrize("command", ["create", "destroy", "start", "stop", "sync"])
# def test_operate_with_instance_name(mocker: MockerFixture, command):
#     mocker.patch("typer.confirm").return_value = True
#     instance_name = "revel1"
#     # Commands that require confirmation
#     if command in ["destroy"]:
#         input = "\n"
#     else:
#         input = None
#     result = runner.invoke(app=cli.app, args=[command, instance_name], input=input)

#     assert result.exit_code == 0, result.output


# @pytest.mark.parametrize("command", ["create", "destroy", "start", "stop", "sync"])
# def test_operate_with_default(mocker: MockerFixture, command):
#     mocker.patch("typer.confirm").return_value = True

#     mm = mocker.create_autospec(MachineManager)
#     mocker.patch("revel.machine.MachineManager", mm)
#     mm.get.return_value = Machine()

#     # Commands that require confirmation
#     if command in ["destroy"]:
#         input = "\n"
#     else:
#         input = None
#     result = runner.invoke(app=cli.app, args=[command], input=input)

#     if command in ["destroy"]:
#         assert mm.get.called

#     assert result.exit_code == 0, result.output
