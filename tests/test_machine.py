from pathlib import Path

import boto3
import pytest
from moto import mock_ec2

from revel import MachineManager


@mock_ec2()
def test_machine_loop():
    name = "mock"
    machine_state_dir = Path("/tmp/")
    mm = MachineManager(
        ec2=boto3.resource("ec2"), machine_state_dir=machine_state_dir, name=name
    )

    mm.create(
        ami="ami-123123123",
        instance_type="t3.fake",
        key_name="gonzalopeci",
    )

    mm.destroy()

    with pytest.raises(NotImplementedError):
        mm.stop()

        mm.start()

        mm.suspend()

        mm.start()
