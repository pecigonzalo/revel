from dataclasses import dataclass
from enum import Enum
from optparse import Option
from pathlib import Path
from typing import Any, Optional, cast

import yaml
from botocore.exceptions import ClientError
from mypy_boto3_ec2.literals import InstanceTypeType, VolumeTypeType
from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
from mypy_boto3_ec2.type_defs import BlockDeviceMappingTypeDef, EbsBlockDeviceTypeDef

from revel.config import Disk, DiskType


class MachineState(str, Enum):
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


@dataclass
class Machine:
    name: str = "default"
    port: int = 22
    user: str = "ec2-user"
    public_ip_address: Optional[str] = None
    private_ip_address: Optional[str] = None
    state: MachineState = MachineState.CREATING
    id: Optional[str] = None

    @classmethod
    def from_object(cls, **kwargs) -> "Machine":
        return cls(
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
    ) -> dict[str, Any]:
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
    machine_state_dir: Path
    machine: Machine
    ec2: EC2ServiceResource

    def __init__(
        self,
        machine_state_dir: Path,
        name: str,
        ec2: EC2ServiceResource,
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

    @staticmethod
    def list(
        machine_state_dir: Path,
        ec2: EC2ServiceResource,
    ) -> list["MachineManager"]:
        return [
            MachineManager(machine_state_dir, file.with_suffix("").name, ec2)
            for file in machine_state_dir.glob("*.yml")
            if file.is_file()
        ]

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
        elif instance:
            self.machine.state = MachineState.from_instance_state(
                instance.state.get("Name")
            )

        if persist:
            self.save()

    def refresh(self) -> Machine:
        self.load()
        if self.machine.id:
            id = self.machine.id
        else:
            raise ValueError("Machine ID not found")

        instance = self.ec2.Instance(id)

        self.update(instance=instance)
        return self.machine

    def load(self) -> Machine:
        instance_state = self._get_machine_state_path()
        if not instance_state.exists():
            raise FileNotFoundError(f"Unable to find {instance_state}")

        with instance_state.open("r") as state_file:
            state = yaml.safe_load(state_file)
            if state:
                self.machine = Machine.from_object(**state)
                return self.machine
            else:
                raise ValueError(f"Unable to load YAML state {state_file.name}")

    def remove(self) -> None:
        instance_state = self._get_machine_state_path()
        instance_state.unlink()

    # TODO: Get or raise, None is problematic here
    def get(self) -> Optional[Machine]:
        try:
            self.load()
            return self.machine if self.machine.id else None
        except FileNotFoundError:
            return None
        except ValueError:
            return None

    def create(
        self,
        ami: str,
        key_name: str,
        size: str = "t3.micro",
        disk: Disk = Disk(),
        port: Optional[int] = None,
        user: Optional[str] = None,
    ) -> Machine:
        if port:
            self.machine.port = port
        if user:
            self.machine.user = user

        # Create a single instance
        self.save()

        # TODO: Can we avoid casting?
        instances = self.ec2.create_instances(
            MaxCount=1,
            MinCount=1,
            ImageId=ami,
            InstanceType=cast(InstanceTypeType, size),
            KeyName=key_name,
            Monitoring={"Enabled": True},
            EbsOptimized=True,
            BlockDeviceMappings=[
                BlockDeviceMappingTypeDef(
                    DeviceName="/dev/sda1", # TODO: This should be a parameter
                    Ebs=EbsBlockDeviceTypeDef(
                        DeleteOnTermination=True,
                        VolumeSize=disk.size,
                        VolumeType=cast(VolumeTypeType, disk.type),
                        Iops=disk.iops,
                    ),
                )
            ],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": self.machine.name}],
                },
                {
                    "ResourceType": "volume",
                    "Tags": [{"Key": "Name", "Value": self.machine.name}],
                },
            ],
        )
        instance: Instance = instances[0]
        self.update(instance, state=MachineState.CREATING)

        instance.wait_until_running()
        return self.refresh()

    def destroy(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)
        try:
            instance.terminate()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", None)
            # InvalidInstanceID.Malformed is returned when instance cannot be found 🤷
            if code in ["InvalidInstanceID.NotFound", "InvalidInstanceID.Malformed"]:
                self.remove()
            else:
                raise e

        self.update(instance, state=MachineState.TERMINATING)
        instance.wait_until_terminated()
        self.remove()

    def stop(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)

        instance.stop()
        instance.wait_until_stopped()
        self.refresh()
        self.update(state=MachineState.STOPPED)

    def start(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)

        instance.start()
        instance.wait_until_running()
        self.refresh()
        self.update(state=MachineState.RUNNING)

    def suspend(self) -> None:
        raise NotImplementedError("Not implemented")
