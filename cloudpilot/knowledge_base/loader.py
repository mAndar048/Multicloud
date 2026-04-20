"""Catalog loading and validation helpers."""

from pathlib import Path
from typing import Any

import yaml


USE_CASES = {"static_website", "containerized_app", "database"}
TRAFFIC_TIERS = ["low", "medium", "high"]
CLOUDS = ["aws", "gcp", "digitalocean"]
REQUIRED_TEMPLATE_FILES = ("main.tf", "variables.tf", "outputs.tf", "meta.yaml")


class CatalogValidationError(Exception):
    """Raised when catalog format or template mappings are invalid."""


def _default_catalog_path() -> Path:
    return Path(__file__).with_name("catalog.yaml")


def _default_templates_root() -> Path:
    return Path(__file__).resolve().parents[1] / "templates"


def _validate_thresholds(raw_catalog: dict[str, Any]) -> None:
    thresholds = raw_catalog.get("thresholds")
    if not isinstance(thresholds, dict):
        raise CatalogValidationError("Catalog must include a 'thresholds' mapping.")

    previous_max: int | None = None
    for tier in TRAFFIC_TIERS:
        tier_data = thresholds.get(tier)
        if not isinstance(tier_data, dict):
            raise CatalogValidationError(f"Missing threshold config for tier '{tier}'.")

        max_users = tier_data.get("max_users")
        if not isinstance(max_users, int) or max_users <= 0:
            raise CatalogValidationError(
                f"thresholds.{tier}.max_users must be a positive integer."
            )

        if previous_max is not None and max_users <= previous_max:
            raise CatalogValidationError("Traffic tier thresholds must increase by tier.")
        previous_max = max_users


def _validate_template_dir(template_dir: Path, mapping: str) -> None:
    if not template_dir.is_dir():
        raise CatalogValidationError(f"Template path '{mapping}' does not exist.")

    for filename in REQUIRED_TEMPLATE_FILES:
        if not (template_dir / filename).is_file():
            raise CatalogValidationError(
                f"Template path '{mapping}' is missing required file '{filename}'."
            )


def _validate_use_case_mappings(
    raw_catalog: dict[str, Any], templates_root: Path, validate_template_paths: bool
) -> None:
    catalog_use_cases = set(raw_catalog.keys()) - {"thresholds"}
    missing_use_cases = USE_CASES - catalog_use_cases
    unexpected_use_cases = catalog_use_cases - USE_CASES

    if missing_use_cases:
        raise CatalogValidationError(
            f"Catalog is missing use cases: {sorted(missing_use_cases)}"
        )
    if unexpected_use_cases:
        raise CatalogValidationError(
            f"Catalog has unknown use cases: {sorted(unexpected_use_cases)}"
        )

    for use_case in USE_CASES:
        use_case_map = raw_catalog.get(use_case)
        if not isinstance(use_case_map, dict):
            raise CatalogValidationError(f"Use case '{use_case}' must map to a dictionary.")

        for tier in TRAFFIC_TIERS:
            tier_map = use_case_map.get(tier)
            if not isinstance(tier_map, dict):
                raise CatalogValidationError(
                    f"Use case '{use_case}' is missing tier mapping '{tier}'."
                )

            missing_clouds = set(CLOUDS) - set(tier_map.keys())
            if missing_clouds:
                raise CatalogValidationError(
                    f"Use case '{use_case}', tier '{tier}' is missing clouds: "
                    f"{sorted(missing_clouds)}"
                )

            for cloud in CLOUDS:
                mapping = tier_map.get(cloud)
                if mapping is None:
                    continue

                if not isinstance(mapping, str) or not mapping.strip():
                    raise CatalogValidationError(
                        f"Mapping for {use_case}/{tier}/{cloud} must be a non-empty string "
                        "or null."
                    )

                if validate_template_paths:
                    _validate_template_dir(templates_root / mapping, mapping)


def load_catalog(
    path: str | Path | None = None,
    *,
    validate_template_paths: bool = True,
) -> dict[str, Any]:
    """Load and validate catalog YAML from disk."""
    catalog_path = Path(path) if path is not None else _default_catalog_path()
    templates_root = _default_templates_root()

    if not catalog_path.exists():
        raise CatalogValidationError(f"Catalog file not found: {catalog_path}")

    with catalog_path.open("r", encoding="utf-8") as handle:
        raw_catalog = yaml.safe_load(handle) or {}

    if not isinstance(raw_catalog, dict):
        raise CatalogValidationError("Catalog root must be a dictionary.")

    _validate_thresholds(raw_catalog)
    _validate_use_case_mappings(raw_catalog, templates_root, validate_template_paths)

    return raw_catalog
