from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import sh


@dataclass()
class SSH:
    user: str
    host: str

    def __post_init__(self):
        ssh_keyscan = sh.Command("ssh-keyscan")
        ssh_keyscan("-4", self.host)

    def run(
        self,
        opts: Optional[list[str]] = field(default_factory=list[str]),
        args: list[str] = field(default_factory=list[str]),
    ) -> sh.Command:
        ssh = sh.Command("ssh")
        command = ssh.bake(
            f"{self.user}@{self.host}",
            *args,
            _fg=True,
        )
        return command

    def sync(
        self,
        src: str,
        dst: str,
        opts: Optional[list[str]] = field(default_factory=list[str]),
        args: list[str] = field(default_factory=list[str]),
    ) -> sh.Command:
        rsync = sh.Command("rsync")
        full_src = Path(src).expanduser()
        command = rsync.bake(
            "-r",
            "-z",
            "-L",  # TODO: Support these attributes in the sync definition
            full_src,
            f"{self.user}@{self.host}:{dst}",
            _fg=True,
        )

        return command
