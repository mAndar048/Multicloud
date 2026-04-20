"""Shared intent schema used across CloudPilot modules."""

from dataclasses import dataclass


@dataclass
class IntentObject:
    """Normalized deployment intent extracted from user input."""

    use_case: str = ""
    traffic_tier: str = ""
    cloud: str = ""
    region: str = ""
    project_name: str = ""
    raw_input: str = ""
    confidence: float = 0.0
