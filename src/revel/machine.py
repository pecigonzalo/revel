from dataclasses import dataclass
from enum import Enum, auto


class State(Enum):
    RUNNING = auto()
    STOPPED = auto()
    SUSPENDED = auto()


@dataclass
class Machine:
    name: str
    address: str
    port: int
    user: str
    state: State
