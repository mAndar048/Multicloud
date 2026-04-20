from cloudpilot.engine.variable_injector import VariableInjectionError, write_tfvars
from cloudpilot.intent.schema import IntentObject
import pytest


def test_write_tfvars_for_static_website(tmp_path) -> None:
    intent = IntentObject(
        use_case="static_website",
        traffic_tier="low",
        cloud="aws",
        region="us-east-1",
        project_name="demo",
    )

    tfvars_path = write_tfvars("aws/static_website", intent, str(tmp_path))
    content = tfvars_path.read_text(encoding="utf-8")

    assert 'project_name = "demo"' in content
    assert 'region = "us-east-1"' in content


def test_write_tfvars_requires_meta_required_vars(tmp_path) -> None:
    intent = IntentObject(
        use_case="database",
        traffic_tier="low",
        cloud="aws",
        region="us-east-1",
        project_name="demo",
    )

    with pytest.raises(VariableInjectionError, match="Missing required Terraform variables"):
        write_tfvars("aws/database", intent, str(tmp_path))


def test_write_tfvars_supports_extra_vars(tmp_path) -> None:
    intent = IntentObject(
        use_case="database",
        traffic_tier="low",
        cloud="aws",
        region="us-east-1",
        project_name="demo",
    )

    tfvars_path = write_tfvars(
        "aws/database",
        intent,
        str(tmp_path),
        extra_vars={"db_password": "super-secret"},
    )
    content = tfvars_path.read_text(encoding="utf-8")

    assert 'db_password = "super-secret"' in content
