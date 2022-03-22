from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .state import State


@dataclass
class Machine:
    name: str
    port: Optional[int] = None
    user: Optional[str] = None
    state: Optional[State] = None
    public_ip_address: Optional[str] = None
    private_ip_address: Optional[str] = None
    id: Optional[str] = None

    @classmethod
    def from_object(cls, **kwargs) -> "Machine":
        return cls(
            name=kwargs["name"],
            port=kwargs["port"],
            user=kwargs["user"],
            public_ip_address=kwargs["public_ip_address"],
            private_ip_address=kwargs["private_ip_address"],
            state=State(kwargs["state"]),
            id=kwargs["id"],
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "port": self.port,
            "user": self.user,
            "public_ip_address": self.public_ip_address,
            "private_ip_address": self.private_ip_address,
            "state": self.state.value if self.state else None,
            "id": self.id,
        }
