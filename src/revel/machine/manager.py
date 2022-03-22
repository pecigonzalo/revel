from pathlib import Path
from typing import Optional, cast

import yaml
from botocore.exceptions import ClientError
from mypy_boto3_ec2.literals import InstanceTypeType, VolumeTypeType
from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
from mypy_boto3_ec2.type_defs import BlockDeviceMappingTypeDef, EbsBlockDeviceTypeDef

from .machine import Machine
from .state import State


class MachineManager:
    state_dir: Path
    machine: Machine
    ec2: EC2ServiceResource

    def __init__(
        self,
        machine: Machine,
        state_dir: Path,
        ec2: EC2ServiceResource,
    ) -> None:
        self.ec2 = ec2
        self.state_dir = state_dir
        self.machine = machine

        # Lazy load config
        try:
            self.load_from_state()
        except Exception:
            pass


    def _machine_state_path(self) -> Path:
        # NOTE: Should this be here? Maybe not
        self.state_dir.mkdir(parents=True, exist_ok=True)

        return Path(f"{self.state_dir}/{self.machine.name}.yml")

    def load_from_state(self) -> Machine:
        instance_state = self._machine_state_path()
        if not instance_state.exists():
            raise FileNotFoundError(f"Unable to find {instance_state}")

        with instance_state.open("r") as state_file:
            state = yaml.safe_load(state_file)
            if state:
                self.machine = Machine.from_object(**state)
                return self.machine
            else:
                raise ValueError(f"Unable to load YAML state {state_file.name}")

    @staticmethod
    def list(
        machine_state_dir: Path,
        ec2: EC2ServiceResource,
    ) -> list["MachineManager"]:
        return [
            MachineManager(Machine(file.with_suffix("").name), machine_state_dir, ec2)
            for file in machine_state_dir.glob("*.yml")
            if file.is_file()
        ]

    def save(self) -> None:
        instance_state = self._machine_state_path()
        with instance_state.open("w") as state_file:
            yaml.safe_dump(
                self.machine.to_dict(), state_file, tags=None, default_flow_style=False
            )

    def update(
        self,
        instance: Optional[Instance] = None,
        state: Optional[State] = None,
        persist: bool = True,
    ) -> None:
        if instance:
            self.machine.id = instance.id
            self.machine.public_ip_address = instance.public_ip_address
            self.machine.private_ip_address = instance.private_ip_address

        if state:
            self.machine.state = state
        elif instance:
            self.machine.state = State.from_instance_state(
                instance.state.get("Name")
            )

        if persist:
            self.save()

    def refresh(self) -> Machine:
        self.load_from_state()
        if self.machine.id:
            id = self.machine.id
        else:
            raise ValueError("Machine ID not found")

        instance = self.ec2.Instance(id)

        self.update(instance=instance)
        return self.machine

    def remove(self) -> None:
        instance_state = self._machine_state_path()
        instance_state.unlink()

    # TODO: Get or raise, None is problematic here
    def get(self) -> Optional[Machine]:
        try:
            self.load_from_state()
            return self.machine if self.machine.id else None
        except FileNotFoundError:
            return None
        except ValueError:
            return None

    def create(
        self,
        ami: str,
        key_name: str,
        port: int,
        user: str,
        instance_size: str,
        volume_size: int,
        volume_type: str,
        volume_iops: int,
    ) -> Machine:
        self.machine.port = port
        self.machine.user = user

        # Create a single instance
        self.save()

        # TODO: Can we avoid casting?
        instances = self.ec2.create_instances(
            MaxCount=1,
            MinCount=1,
            ImageId=ami,
            InstanceType=cast(InstanceTypeType, instance_size),
            KeyName=key_name,
            Monitoring={"Enabled": True},
            EbsOptimized=True,
            BlockDeviceMappings=[
                BlockDeviceMappingTypeDef(
                    DeviceName="/dev/sda1", # TODO: This should be a parameter
                    Ebs=EbsBlockDeviceTypeDef(
                        DeleteOnTermination=True,
                        VolumeSize=volume_size,
                        VolumeType=cast(VolumeTypeType, volume_type),
                        Iops=volume_iops,
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
        self.update(instance, state=State.CREATING)

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

        self.update(instance, state=State.TERMINATING)
        instance.wait_until_terminated()
        self.remove()

    def stop(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)

        instance.stop()
        instance.wait_until_stopped()
        self.refresh()
        self.update(state=State.STOPPED)

    def start(self) -> None:
        if not self.machine.id:
            raise ValueError(f"Unable to find machine ID for {self.machine.name}")

        instance = self.ec2.Instance(self.machine.id)

        instance.start()
        instance.wait_until_running()
        self.refresh()
        self.update(state=State.RUNNING)

    def suspend(self) -> None:
        raise NotImplementedError("Not implemented")
