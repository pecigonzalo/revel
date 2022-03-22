from pathlib import Path

from revel import config


def test_full_config_load():
    result = config.Config(Path("./tests/mock/full_config.yml"))

    assert isinstance(result, config.Config), "Config should be able to load"

    assert result.instances, "Configuration should have loaded mock instsancess"

    for k, v in result.instances.items():
        assert isinstance(
            v, config.InstanceConfig
        ), f"Instances {k} should be of type Instance"
