from enum import Enum
from typing import Optional


class State(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    STOPPING = "STOPPING"
    SUSPENDED = "SUSPENDED"
    CREATING = "CREATING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_instance_state(cls, state: Optional[str]) -> "MachineState":
        instance_state_map = {
            "pending": cls.PENDING,
            "running": cls.RUNNING,
            "shutting-down": cls.TERMINATING,
            "terminated": cls.TERMINATED,
            "stopping": cls.STOPPING,
            "stopped": cls.STOPPED,
        }

        if not state:
            return cls.UNKNOWN

        return instance_state_map.get(state, cls.UNKNOWN)
