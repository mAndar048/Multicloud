"""Template selection logic."""

from pathlib import Path

from cloudpilot.intent.schema import IntentObject
from cloudpilot.knowledge_base.loader import load_catalog


class TemplateNotFoundError(Exception):
    """Raised when no template matches intent."""


def select_template(intent: IntentObject) -> str:
    """Return a template path for the given intent."""
    required_fields = {
        "use_case": intent.use_case,
        "traffic_tier": intent.traffic_tier,
        "cloud": intent.cloud,
    }
    missing = [field for field, value in required_fields.items() if not value]
    if missing:
        raise ValueError(
            "Cannot select template. Missing intent fields: " + ", ".join(missing)
        )

    catalog = load_catalog()

    try:
        mapping = catalog[intent.use_case][intent.traffic_tier][intent.cloud]
    except KeyError as exc:
        raise TemplateNotFoundError(
            "No template mapping found for "
            f"use_case='{intent.use_case}', "
            f"traffic_tier='{intent.traffic_tier}', "
            f"cloud='{intent.cloud}'."
        ) from exc

    if mapping is None:
        raise TemplateNotFoundError(
            "Template not available yet for "
            f"use_case='{intent.use_case}', "
            f"traffic_tier='{intent.traffic_tier}', "
            f"cloud='{intent.cloud}'."
        )

    templates_root = Path(__file__).resolve().parents[1] / "templates"
    return str(templates_root / mapping)
