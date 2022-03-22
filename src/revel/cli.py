from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import List, Optional

import boto3
import typer
from botocore.exceptions import BotoCoreError
from halo import Halo
from sh import ErrorReturnCode  # TODO: This is a bit too leaky
from tabulate import tabulate

from . import __name__ as cli_name
from . import __version__ as cli_version
from .config import Config, DiskConfig, RunCommand, SyncFiles
from .machine import Machine, MachineManager
from .providers.ssh import SSH
from .state import state

app = typer.Typer()


def get_ec2_resource():
    # TODO: Replace with better an abstraction. This is an aweful hack to get this going.
    # We might want to replace/abstract MachineManager
    # and instantiate it only once here.
    try:
        return boto3.Session().resource("ec2")
    except BotoCoreError as e:
        typer.secho(
            f"An error occurred while setting up the AWS session: {e}",
            fg=typer.colors.RED,
        )
        raise e


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
    SESSION = get_ec2_resource()

    machine = MachineManager(
        Machine(name),
        STATE_DIR,
        SESSION,
    ).machine
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

    if not machine.user:
        typer.echo("Machine has no user defined")
        raise typer.Exit()

    client = SSH(user=machine.user, host=machine.public_ip_address)
    for init in instance_config.init:
        if type(init) is SyncFiles:
            for src, dst in init:
                typer.echo(f"Uploading file {src} to {dst}")
                command = client.sync(src=src, dst=dst)
                if DEBUG:
                    typer.echo(command)
                try:
                    command()
                except ErrorReturnCode:
                    raise typer.Abort()

        elif type(init) is RunCommand:
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
    SESSION = get_ec2_resource()
    instances = CONFIG.instances
    if not instances:
        typer.echo("Unable to find instances in the configuration")
        raise typer.Abort()

    instance_config = instances.get(name)
    if not instance_config:
        typer.echo(f"Unable to find instance {name}")
        raise typer.Abort()

    mm = MachineManager(
        Machine(name),
        STATE_DIR,
        SESSION,
    )
    machine = mm.machine

    if machine.id:
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
            if (disk := instance_config.disk):
                volume_size = disk.size
                volume_type = disk.type
                volume_iops = disk.iops
            else:
                disk = DiskConfig()
                volume_size = disk.size
                volume_type = disk.type
                volume_iops = disk.iops


            machine = mm.create(
                ami=instance_config.ami,
                instance_size=instance_config.size,
                volume_type=volume_type,
                volume_size=volume_size,
                volume_iops=volume_iops,
                key_name=instance_config.key or "",
                user=instance_config.user,
                port=instance_config.port,
            )

        typer.echo(f"Instance id: {machine.id}")
        typer.echo("Connection information:")
        typer.echo(f"Public IP: {machine.public_ip_address}")


@app.command()
def destroy(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    if all:
        typer.confirm(
            "😱 About to destroy all machines, Do you want to continue?", abort=True
        )
        managers = MachineManager.list(STATE_DIR, SESSION)
    else:
        typer.confirm(
            f"💣 About to destroy {name}, do you want to continue?", abort=True
        )
        managers = [
            MachineManager(
                Machine(name),
                STATE_DIR,
                SESSION,
            )
        ]

    for mm in managers:
        typer.echo(f"Deleting instance {mm.machine.name}...")
        with Halo(
            text="Waiting for instance to be destroyed...",
            spinner="bouncingBar",
            color="green",
        ):
            mm.destroy()

        typer.echo(f"Instance {mm.machine.name} deleted 🎉")
        # else:
        #     typer.echo(f"Instance {mm.machine.name} does not exist 🤷")


class ListFormat(str, Enum):
    plain = "plain"
    simple = "simple"
    github = "github"


# We have to alias the function to avoid collition with typing
@app.command(name="list")
def list_machines(
    ctx: typer.Context,
    format: ListFormat = ListFormat.simple,
    fields: list[str] = typer.Option(
        ["name", "private_ip_address:ip", "state"], "--field"
    ),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    machines = [mm.machine for mm in MachineManager.list(STATE_DIR, SESSION)]

    aliases = [
        field.split(":")[1] if field.split(":")[1:] else field.split(":")[0]
        for field in fields
    ]
    fields = [field.split(":")[0] for field in fields]

    headers = [alias.title().replace("_", " ") for alias in aliases]
    body = [
        [getattr(machine, field.lower()) for field in fields] for machine in machines
    ]

    table = tabulate(
        body,
        headers=headers,
        tablefmt=format,
    )

    typer.echo(table)


@app.command()
def refresh(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    if all:
        managers = MachineManager.list(STATE_DIR, SESSION)
    else:
        managers = [
            MachineManager(
                Machine(name),
                STATE_DIR,
                SESSION,
            )
        ]

    with typer.progressbar(managers, label="Refreshing") as progress:
        for manager in progress:
            manager.refresh()


@app.command()
def ssh(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    print: bool = typer.Option(False),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    machine = MachineManager(
        Machine(name),
        STATE_DIR,
        SESSION,
    ).machine
    if not machine:
        typer.echo(f"Instance {name} does not exist")
        raise typer.Exit()

    if not machine.public_ip_address:
        typer.echo(f"Instance {name} has no public IP")
        raise typer.Exit()

    if not machine.user:
        typer.echo("Machine has no user defined")
        raise typer.Exit()

    client = SSH(machine.user, machine.public_ip_address)
    command = client.run(args=[])
    if print:
        typer.echo(command)
    else:
        command()


@app.command()
def start(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    if all:
        managers = MachineManager.list(STATE_DIR, SESSION)
    else:
        managers = [MachineManager(Machine(name), STATE_DIR, SESSION,)]

    with typer.progressbar(managers, label="Starting") as progress:
        for manager in progress:
            manager.start()


@app.command()
def stop(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
    all: bool = typer.Option(False, "--all"),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    if all:
        managers = MachineManager.list(STATE_DIR, SESSION)
    else:
        managers = [MachineManager(Machine(name), STATE_DIR, SESSION)]

    with typer.progressbar(managers, label="Stopping") as progress:
        for manager in progress:
            manager.stop()


@app.command()
def sync(
    ctx: typer.Context,
    name: str = typer.Argument(default="default"),
):
    CONFIG = Config(ctx.obj["config"])
    STATE_DIR = ctx.obj["state"]
    DEBUG = ctx.obj["debug"]
    SESSION = get_ec2_resource()
    machine = MachineManager(
        Machine(name),
        STATE_DIR,
        SESSION,
    ).machine
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

    if not machine.user:
        typer.echo("Machine has no user defined")
        raise typer.Exit()

    client = SSH(machine.user, machine.public_ip_address)
    for src, dst in instance_config.sync:
        typer.echo(f"Uploading file {src} to {dst}")
        command = client.sync(src=src, dst=dst)
        if DEBUG:
            typer.echo(command)
        try:
            command()
        except ErrorReturnCode:
            raise typer.Abort()


@app.command()
def ssh_config(
    ctx: typer.Context,
    file: typer.FileTextWrite = typer.Option(
        f"{Path.home()}/.ssh/revel.config",
        show_default=False,
        show_envvar=False,
        help="[default: ~/.ssh/revel.config]",
    ),
    name: str = typer.Argument(default="default"),
    print: bool = typer.Option(False),
):
    STATE_DIR = ctx.obj["state"]
    SESSION = get_ec2_resource()
    machine = MachineManager(Machine(name), STATE_DIR, SESSION).machine
    if not machine:
        typer.echo(f"Instance {name} does not exist")
        raise typer.Exit()

    if not machine.public_ip_address:
        typer.echo(f"Instance {name} has no public IP")
        raise typer.Exit()

    # host = f"{machine.user}@{machine.host}"

    config = dedent(
        f"""\
    Host {name}.revel
        User {machine.user}
        Hostname {machine.public_ip_address}
    """
    )

    if print:
        typer.echo(config)
    else:
        file.write(config)


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
