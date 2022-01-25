from pathlib import Path
from typing import List, Optional

import boto3
import typer
import yaml
from halo import Halo
from sh import ErrorReturnCode  # TODO: This is a bit leaky

from revel import Config
from revel import __name__ as cli_name
from revel import __version__ as cli_version
from revel.clients import SSH
from revel.config import InitFiles, InitRun
from revel.machine import MachineManager
from revel.state import state

app = typer.Typer()


@app.command()
def provision(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    # NOTE: Using List instead of list because mypy is complaining
    extra: Optional[List[str]] = typer.Option(None),
):
    CONFIG = Config(ctx.obj["config"])
    STATE_DIR = ctx.obj["state"]
    DEBUG = ctx.obj["debug"]

    mm = MachineManager(
        boto3.resource("ec2"),
        STATE_DIR,
        name,
    )
    machine = mm.get()
    if not machine:
        typer.echo(f"Instance {name} does not exist")
        raise typer.Exit()

    if not machine.public_ip_address:
        typer.echo(f"Instance {name} has no public IP")
        raise typer.Exit()

    instance_config = CONFIG.instances.get(name)
    if not instance_config:
        typer.echo("Failed to find instance config")
        raise typer.Exit()

    client = SSH(user=machine.user, host=machine.public_ip_address)
    for init in instance_config.init:
        if type(init) is InitFiles:
            for src, dst in init:
                typer.echo(f"Uploading file {src} to {dst}")
                command = client.sync(src=src, dst=dst)
                if DEBUG:
                    typer.echo(command)
                try:
                    command()
                except ErrorReturnCode:
                    raise typer.Abort()

        elif type(init) is InitRun:
            typer.echo(f"Executing {init}")
            command = client.run(
                opts=extra,
                args=[init],
            )
            if DEBUG:
                typer.echo(command)
            try:
                command()
            except ErrorReturnCode:
                raise typer.Abort()
        else:
            typer.echo(f"Unkown type {type(init)} for {init}")


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
):
    CONFIG = Config(ctx.obj["config"])
    STATE_DIR = ctx.obj["state"]
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
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    if all:
        typer.confirm(
            "😱 About to destroy all machines, Do you want to continue?", abort=True
        )
        machines = MachineManager.list(STATE_DIR)
    else:
        typer.confirm(
            f"💣 About to destroy {name}, do you want to continue?", abort=True
        )
        machines = [name]

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
def list(
    ctx: typer.Context,
):
    STATE_DIR = ctx.obj["state"]
    machines = MachineManager.list(STATE_DIR)
    typer.echo(yaml.safe_dump(machines))


@app.command()
def refresh(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    if all:
        machines = MachineManager.list(STATE_DIR)
    else:
        machines = [name]

    with typer.progressbar(machines, label="Refreshing") as progress:
        for machine in progress:
            mm = MachineManager(
                boto3.resource("ec2"),
                STATE_DIR,
                machine,
            )
            mm.refresh()


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
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
    debug: bool = typer.Option(state["debug"]),
    config: Path = typer.Option(state["config"]),
):
    ctx.obj = state
    ctx.obj["config"] = config
    ctx.obj["debug"] = debug
