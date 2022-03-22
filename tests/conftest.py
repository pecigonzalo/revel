from pathlib import Path

import pytest

import revel


@pytest.fixture(autouse=True, scope="function")
def mock_aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")


@pytest.fixture(autouse=True)
def mock_state_conf(monkeypatch, tmp_path):
    # Application of the monkeypatch to replace Path.home
    # with the behavior of mockreturn defined above.
    monkeypatch.setattr(
        revel,
        "state",
        {
            "config": Path("tests/mock/full_config.yml"),
            "state": tmp_path,
        },
    )
