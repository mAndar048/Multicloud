import pytest

from cloudpilot.engine.template_selector import TemplateNotFoundError, select_template
from cloudpilot.intent.schema import IntentObject


def test_select_template_success() -> None:
    intent = IntentObject(
        use_case="static_website",
        traffic_tier="low",
        cloud="aws",
    )

    assert select_template(intent) == "aws/static_website"


def test_select_template_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="Missing intent fields"):
        select_template(IntentObject())


def test_select_template_unavailable_combination() -> None:
    intent = IntentObject(
        use_case="database",
        traffic_tier="low",
        cloud="digitalocean",
    )

    with pytest.raises(TemplateNotFoundError, match="not available yet"):
        select_template(intent)
