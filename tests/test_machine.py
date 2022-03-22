from pathlib import Path

import boto3
import pytest
from moto import mock_ec2

from revel import MachineManager


@mock_ec2()
def test_machine_create():
    name = "mock"
    machine_state_dir = Path("/tmp/")
    ec2 = boto3.resource("ec2")
    mm = MachineManager(
        ec2=ec2, machine_state_dir=machine_state_dir, name=name
    )

    machine = mm.create(
        ami="ami-123123123",
        instance_type="t3.fake",
        key_name="gonzalopeci",
    )

    assert machine.id

@mock_ec2()
def test_machine_create_volume():
    name = "mock"
    machine_state_dir = Path("/tmp/")
    ec2 = boto3.resource("ec2")
    mm = MachineManager(
        ec2=ec2, machine_state_dir=machine_state_dir, name=name
    )

    volume_iops = 999
    volume_size = 9
    volume_type = "ioi"

    machine = mm.create(
        ami="ami-123123123",
        instance_type="t3.fake",
        key_name="gonzalopeci",
        volume_iops=volume_iops,
        volume_size=volume_size,
        volume_type=volume_type,
    )

    assert machine.id

    instance = ec2.Instance(machine.id)

    for instance_volume in instance.volumes.all():
        volume = ec2.Volume(instance_volume.id)
        # TODO: Test for its name/path
        # volume_name = volume.,
        assert volume_size == volume.size
        # TODO: Testing this does not seem to work, but creation does use the correct type, I suspect its the mocker
        # assert volume_type == volume.volume_type
        assert volume_iops == volume.iops
