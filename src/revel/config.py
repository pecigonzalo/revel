from collections import UserList
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import yaml


class DiskType(str, Enum):
    GP3 = "gp3"
    GP2 = "gp2"
    IO1 = "io1"


@dataclass
class Disk:
    type: DiskType = DiskType.GP3
    size: int = 10
    iops: int = 3000


SyncFile = tuple[str, str]


class SyncFiles(UserList[SyncFile]):
    pass


RunCommand = str

Init = Union[SyncFiles, RunCommand]


@dataclass
class Instance:
    ami: str
    user: str = "ec2-user"
    key: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    profile: Optional[str] = None
    public: bool = True  # TODO: Review if we can make it with SSM
    port: int = 22
    size: str = "t3.micro"
    disk: Optional[Disk] = None
    backups: bool = False
    auto_shutdown: bool = True
    init: list[Init] = field(default_factory=list[Init])
    sync: list[SyncFile] = field(default_factory=list[SyncFile])

    @staticmethod
    def parse(**kwargs) -> "Instance":
        init: list[Init] = []
        for i in kwargs.get("init", []):
            if i.get("files", None):
                # Create touple of files to sync
                init_files = SyncFiles(
                    [
                        (file.split(":")[0], file.split(":")[1])
                        for file in i.get("files")
                    ]
                )
                init.append(init_files)
            elif i.get("run", None):
                run = i.get("run")
                init.append(run)

        sync: list[SyncFile] = []
        for file in kwargs.get("sync", []):
            # Create touple of files to sync
            sync_files = (file.split(":")[0], file.split(":")[1])
            sync.append(sync_files)

        disk = kwargs.get("disk", None)

        return Instance(
            ami=kwargs.get("ami", None),
            user=kwargs.get("user", None),
            name=kwargs.get("name", None),
            key=kwargs.get("key", None),
            description=kwargs.get("description", None),
            profile=kwargs.get("profile", None),
            public=kwargs.get("public", None),
            size=kwargs.get("size", None),
            disk=Disk(**disk) if disk else None,
            backups=kwargs.get("backups", None),
            auto_shutdown=kwargs.get("auto_shutdown", None),
            init=init,
            sync=sync,
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
