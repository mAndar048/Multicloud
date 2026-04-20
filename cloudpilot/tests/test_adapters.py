import pytest

from cloudpilot.adapters.aws_adapter import AWSAdapter
from cloudpilot.adapters.base import AdapterCredentialsError
from cloudpilot.adapters.do_adapter import DOAdapter
from cloudpilot.adapters.gcp_adapter import GCPAdapter


def test_aws_adapter_success() -> None:
    env = AWSAdapter().get_env_vars(
        {"access_key": "ak", "secret_key": "sk", "region": "us-east-1"}
    )
    assert env["AWS_ACCESS_KEY_ID"] == "ak"


def test_aws_adapter_missing_required_fields() -> None:
    with pytest.raises(AdapterCredentialsError, match="secret_key"):
        AWSAdapter().get_env_vars({"access_key": "ak", "region": "us-east-1"})


def test_gcp_adapter_success() -> None:
    env = GCPAdapter().get_env_vars(
        {"project_id": "p1", "credentials_path": "creds.json"}
    )
    assert env["GOOGLE_CLOUD_PROJECT"] == "p1"


def test_gcp_adapter_missing_required_fields() -> None:
    with pytest.raises(AdapterCredentialsError, match="credentials_path"):
        GCPAdapter().get_env_vars({"project_id": "p1"})


def test_do_adapter_success() -> None:
    env = DOAdapter().get_env_vars({"token": "abc"})
    assert env["DIGITALOCEAN_TOKEN"] == "abc"


def test_do_adapter_missing_required_fields() -> None:
    with pytest.raises(AdapterCredentialsError, match="token"):
        DOAdapter().get_env_vars({})
