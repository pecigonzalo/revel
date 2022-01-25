from collections import UserList
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


InitFile = tuple[str, str]


class InitFilesClass(UserList[InitFile]):
    pass


InitFiles = InitFilesClass

InitRun = str

Init = Union[InitFiles, InitRun]


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
    init: list[Init] = field(default_factory=list[Init])
    sync: list[str] = field(default_factory=list[str])

    @staticmethod
    def parse(**kwargs) -> "Instance":
        init: list[Init] = []
        for i in kwargs.get("init", []):
            if i.get("files", None):
                # Create touple of files to sync
                files: InitFiles = InitFilesClass(
                    [
                        (file.split(":")[0], file.split(":")[1])
                        for file in i.get("files")
                    ]
                )
                init.append(files)
            elif i.get("run", None):
                run = i.get("run")
                init.append(run)

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
            init=init,
            sync=[i for i in kwargs.get("sync", [])],
        )


Instances = dict[str, Instance]


class Config:
    instances: Instances

    def load(self, path: Path) -> None:
        with open(path, "r") as config:
            yaml_config = yaml.safe_load(config)
            self.instances = {k: Instance.parse(**v) for k, v in yaml_config.items()}

    def __init__(self, path: Path):
        self.load(path)
