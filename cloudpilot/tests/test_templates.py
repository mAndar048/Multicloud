from pathlib import Path

import pytest

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

REQUIRED_TEMPLATES = [
    TEMPLATE_DIR / "aws" / "static_website",
    TEMPLATE_DIR / "aws" / "containerized_app",
    TEMPLATE_DIR / "aws" / "database",
    TEMPLATE_DIR / "gcp" / "static_website",
    TEMPLATE_DIR / "gcp" / "containerized_app",
    TEMPLATE_DIR / "gcp" / "database",
    TEMPLATE_DIR / "digitalocean" / "static_website",
]


@pytest.mark.parametrize("template_path", REQUIRED_TEMPLATES)
def test_template_has_required_files(template_path: Path) -> None:
    for filename in ["main.tf", "variables.tf", "outputs.tf", "meta.yaml"]:
        assert (template_path / filename).exists(), f"Missing {filename} in {template_path}"


@pytest.mark.parametrize("template_path", REQUIRED_TEMPLATES)
def test_outputs_include_contract_keys(template_path: Path) -> None:
    outputs_content = (template_path / "outputs.tf").read_text(encoding="utf-8")

    assert 'output "endpoint_url"' in outputs_content
    assert 'output "resource_id"' in outputs_content


@pytest.mark.parametrize("template_path", REQUIRED_TEMPLATES)
def test_variables_include_common_names(template_path: Path) -> None:
    vars_content = (template_path / "variables.tf").read_text(encoding="utf-8")

    assert 'variable "project_name"' in vars_content
    assert 'variable "region"' in vars_content
