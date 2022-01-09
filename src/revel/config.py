from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Union

import yaml


class DiskType(Enum):
    GP2 = auto()
    IO1 = auto()


@dataclass
class Disk:
    type: DiskType
    size: int


InitFile = list[str]
InitRun = str

Init = Union[InitFile, InitRun]


@dataclass()
class Instance:
    ami: str
    user: str
    name: Optional[str] = None
    description: Optional[str] = None
    profile: Optional[str] = None
    public: bool = True  # TODO: Review if we can make it with SSM
    size: str = "t3.micro"
    disk: Optional[Disk] = None
    backups: bool = False
    auto_shutdown: bool = True
    init: list[Init] = field(default_factory=list)
    sync: list[str] = field(default_factory=list)


Instances = dict[str, Instance]


@dataclass
class Config:
    instances: Optional[Instances] = None

    def load(self, path: Path) -> None:
        with open(path, "r") as config:
            yaml_config = yaml.safe_load(config)
            self.instances = {k: Instance(**v) for k, v in yaml_config.items()}

    def __init__(self, path: Optional[Path] = None) -> None:
        if path:
            self.load(path)
