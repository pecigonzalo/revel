from pathlib import Path

import typer

from revel import Config
from revel import __name__ as cli_name

# TODO: Move load to init and create config if missing
CONFIG = Config(Path("tests/mock/full_config.yml"))
# CONFIG = Config(Path(f"{typer.get_app_dir(cli_name)}/config.yml"))
STATE_DIR = Path(f"{typer.get_app_dir(cli_name)}/state")
