from typing import Optional

import boto3
import typer
import yaml
from halo import Halo

from revel import CONFIG, STATE_DIR
from revel import __name__ as cli_name
from revel import __version__ as cli_version
from revel.machine import MachineManager

app = typer.Typer()


@app.command()
def create(name: str = typer.Argument(default="default")):
    instances = CONFIG.instances
    if not instances:
        typer.echo("Unable to find instances in the configuration")
        raise typer.Abort()

    instance_config = instances.get(name)
    if not instance_config:
        typer.echo(f"Unable to find instance {name}")
        raise typer.Abort()

    mm = MachineManager(
        ec2=boto3.resource("ec2"),
        machine_state_dir=STATE_DIR,
        name=name,
    )

    machine = mm.get()

    if machine:
        typer.echo(f'Instance "{name}" already exists')
        typer.echo(f"Instance id: {machine.id}")
        typer.echo("Connection information:")
        typer.echo(f"Public IP: {machine.public_ip_address}")
    else:
        typer.echo(f"Creating instance {name}...")
        with Halo(
            text="Waiting for instance to be created...",
            spinner="bouncingBar",
            color="green",
        ):
            machine = mm.create(
                ami=instance_config.ami,
                instance_type=instance_config.size,
                key_name="gonzalopeci",
            )

        typer.echo(f"Instance id: {machine.id}")
        typer.echo("Connection information:")
        typer.echo(f"Public IP: {machine.public_ip_address}")

    # TODO: Implement connection information


@app.command()
def destroy(
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    if all:
        typer.confirm(
            "😱 About to destroy all machines, Do you want to continue?", abort=True
        )
        machines = MachineManager.list(STATE_DIR)
    else:
        typer.confirm(
            f"💣 About to destroy {name}, do you want to continue?", abort=True
        )
        machines = ["name"]

    for machine in machines:
        mm = MachineManager(
            boto3.resource("ec2"),
            STATE_DIR,
            machine,
        )

        machine = mm.get()

        if machine:
            typer.echo(f"Deleting instance {machine}...")
            with Halo(
                text="Waiting for instance to be destroyed...",
                spinner="bouncingBar",
                color="green",
            ):
                mm.destroy()

            typer.echo(f"Instance {machine} deleted 🎉")
        else:
            typer.echo(f"Instance {machine} does not exist 🤷")


@app.command()
def list():
    machines = MachineManager.list(STATE_DIR)
    typer.echo(yaml.safe_dump(machines))


@app.command()
def start(name: str = typer.Argument(default="default")):
    pass


@app.command()
def stop(name: str = typer.Argument(default="default")):
    pass


@app.command()
def sync(name: str = typer.Argument(default="default")):
    pass


def version_callback(value: bool):
    if value:
        typer.echo(cli_version)
        raise typer.Exit()


@app.callback(no_args_is_help=True, context_settings={"auto_envvar_prefix": cli_name})
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):
    """ """
    pass
