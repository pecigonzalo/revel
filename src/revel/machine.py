from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, cast

import yaml
from mypy_boto3_ec2.literals import InstanceTypeType, ResourceTypeType
from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance


class MachineState(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    SUSPENDED = "SUSPENDED"
    CREATING = "CREATING"
    TERMINATING = "TERMINATING"


@dataclass
class Machine:
    name: str = "default"
    port: int = 22
    user: str = "ec2-user"
    public_ip_address: Optional[str] = None
    private_ip_address: Optional[str] = None
    state: MachineState = MachineState.CREATING
    id: Optional[str] = None

    @staticmethod
    def parse(**kwargs) -> "Machine":
        return Machine(
            name=kwargs["name"],
            port=kwargs["port"],
            user=kwargs["user"],
            public_ip_address=kwargs["public_ip_address"],
            private_ip_address=kwargs["private_ip_address"],
            state=MachineState(kwargs["state"]),
            id=kwargs["id"],
        )

    def to_dict(
        self,
    ) -> object:
        return {
            "name": self.name,
            "port": self.port,
            "user": self.user,
            "public_ip_address": self.public_ip_address,
            "private_ip_address": self.private_ip_address,
            "state": self.state.value,
            "id": self.id,
        }


class MachineManager:
    ec2: EC2ServiceResource
    machine_state_dir: Path
    machine: Machine

    def __init__(
        self, ec2: EC2ServiceResource, machine_state_dir: Path, name: str
    ) -> None:
        self.ec2 = ec2
        self.machine_state_dir = machine_state_dir
        self.machine = Machine(name=name)

        # Lazy load config
        try:
            self.load()
        except Exception:
            pass

    def _get_machine_state_path(self) -> Path:
        self.machine_state_dir.mkdir(parents=True, exist_ok=True)

        return Path(f"{self.machine_state_dir}/{self.machine.name}.yml")

    def save(self) -> None:
        instance_state = self._get_machine_state_path()
        with instance_state.open("w") as state_file:
            yaml.safe_dump(
                self.machine.to_dict(), state_file, tags=None, default_flow_style=False
            )

    def update(
        self,
        instance: Optional[Instance] = None,
        state: Optional[MachineState] = None,
        persist: bool = True,
    ) -> None:
        if instance:
            self.machine.id = instance.id
            self.machine.public_ip_address = instance.public_ip_address
            self.machine.private_ip_address = instance.private_ip_address

        if state:
            self.machine.state = state

        if persist:
            self.save()

    def load(self) -> Optional[Machine]:
        instance_state = self._get_machine_state_path()
        if not instance_state.exists():
            raise FileNotFoundError(f"Unable to find {instance_state}")

        with instance_state.open("r") as state_file:
            state = yaml.safe_load(state_file)
            if state:
                self.machine = Machine.parse(**state)
                return self.machine
            else:
                return None

    def remove(self) -> None:
        instance_state = self._get_machine_state_path()
        instance_state.unlink()

    def get(self) -> Optional[Machine]:
        try:
            if self.load():
                return self.machine if self.machine.id else None
            else:
                return None
        except FileNotFoundError:
            return None

    def create(
        self,
        ami: str,
        instance_type: str,
        key_name: str,
        port: Optional[int] = None,
        user: Optional[str] = None,
    ) -> Machine:
        if port:
            self.machine.port = port
        if user:
            self.machine.user = user

        # Create a single instance
        self.update()
        instances = self.ec2.create_instances(
            MaxCount=1,
            MinCount=1,
            ImageId=ami,
            InstanceType=cast(InstanceTypeType, instance_type),
            KeyName=key_name,
            Monitoring={"Enabled": True},
            EbsOptimized=True,
            TagSpecifications=[
                {
                    "ResourceType": cast(ResourceTypeType, "instance"),
                    "Tags": [{"Key": "Name", "Value": self.machine.name}],
                },
                {
                    "ResourceType": cast(ResourceTypeType, "volume"),
                    "Tags": [{"Key": "Name", "Value": self.machine.name}],
                },
            ],
        )
        instance: Instance = instances[0]
        self.update(instance, state=MachineState.CREATING)

        instance.wait_until_running()
        self.update(instance, state=MachineState.RUNNING)
        return self.machine

    def destroy(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)
        instance.terminate()
        self.update(instance, state=MachineState.TERMINATING)
        instance.wait_until_terminated()
        self.remove()

    def stop(self) -> None:
        raise NotImplementedError("Not implemented")

    def start(self) -> None:
        raise NotImplementedError("Not implemented")

    def suspend(self) -> None:
        raise NotImplementedError("Not implemented")
