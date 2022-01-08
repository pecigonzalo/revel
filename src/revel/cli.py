from typing import Optional

import typer

from revel import __name__ as cli_name
from revel import __version__ as cli_version

app = typer.Typer()


@app.command()
def create(name: Optional[str] = typer.Argument(None)):
    pass


@app.command()
def delete(name: Optional[str] = typer.Argument(None)):
    pass


@app.command()
def start(name: Optional[str] = typer.Argument(None)):
    pass


@app.command()
def stop(name: Optional[str] = typer.Argument(None)):
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
