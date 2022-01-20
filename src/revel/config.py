from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import yaml


class DiskType(Enum):
    GP2 = "GP2"
    IO1 = "IO1"


@dataclass
class Disk:
    type: DiskType
    size: int


InitFile = list[str]
InitRun = str

Init = Union[InitFile, InitRun]


@dataclass
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

    @staticmethod
    def parse(**kwargs) -> "Instance":
        return Instance(
            ami=kwargs.get("ami", None),
            user=kwargs.get("user", None),
            name=kwargs.get("name", None),
            description=kwargs.get("description", None),
            profile=kwargs.get("profile", None),
            public=kwargs.get("public", None),
            size=kwargs.get("size", None),
            disk=kwargs.get("disk", None),
            backups=kwargs.get("backups", None),
            auto_shutdown=kwargs.get("auto_shutdown", None),
            init=[i for i in kwargs.get("init", [])],
            sync=[i for i in kwargs.get("sync", [])],
        )


Instances = dict[str, Instance]


class Config:
    instances: Optional[Instances] = None

    def load(self, path: Path) -> None:
        with open(path, "r") as config:
            yaml_config = yaml.safe_load(config)
            self.instances = {k: Instance.parse(**v) for k, v in yaml_config.items()}

    def __init__(self, path: Optional[Path] = None) -> None:
        if path:
            self.load(path)
