from pathlib import Path

import pytest

from cloudpilot.knowledge_base.loader import CatalogValidationError, load_catalog


def test_load_catalog_default_is_valid() -> None:
    catalog = load_catalog()

    assert "thresholds" in catalog
    assert "static_website" in catalog


def test_load_catalog_rejects_missing_thresholds(tmp_path: Path) -> None:
    invalid = tmp_path / "catalog.yaml"
    invalid.write_text(
        """
static_website:
  low:
    aws: aws/static_website
    gcp: gcp/static_website
    digitalocean: digitalocean/static_website
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError, match="thresholds"):
        load_catalog(invalid, validate_template_paths=False)
