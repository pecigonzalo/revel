from pathlib import Path

import typer

from revel import __name__ as cli_name

state = {
    "config": Path("./revel.yml"),
    "state": Path(f"{typer.get_app_dir(cli_name)}/state"),
    "debug": False,
}
