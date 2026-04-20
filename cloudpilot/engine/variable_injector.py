"""Terraform variable file generation."""

import json
import re
from pathlib import Path
from typing import Any

import yaml

from cloudpilot.intent.schema import IntentObject


class VariableInjectionError(Exception):
    """Raised when tfvars cannot be generated safely."""


def _templates_root() -> Path:
    return Path(__file__).resolve().parents[1] / "templates"


def _resolve_template_dir(template_path: str) -> Path:
    candidate = Path(template_path)
    if candidate.is_absolute():
        template_dir = candidate
    else:
        template_dir = _templates_root() / template_path

    if not template_dir.is_dir():
        raise VariableInjectionError(f"Template directory does not exist: {template_dir}")
    return template_dir


def _load_variable_names(template_dir: Path) -> list[str]:
    variables_file = template_dir / "variables.tf"
    if not variables_file.is_file():
        raise VariableInjectionError(f"Missing variables.tf in template: {template_dir}")

    content = variables_file.read_text(encoding="utf-8")
    return re.findall(r'variable\s+"([a-zA-Z0-9_]+)"', content)


def _load_required_vars(template_dir: Path) -> list[str]:
    meta_file = template_dir / "meta.yaml"
    if not meta_file.is_file():
        return []

    meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
    required_vars = meta.get("required_vars", [])
    return [var for var in required_vars if isinstance(var, str)]


def _to_hcl(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return json.dumps(str(value))


def write_tfvars(
    template_path: str,
    intent: IntentObject,
    workspace_dir: str,
    extra_vars: dict[str, Any] | None = None,
) -> Path:
    """Write terraform.tfvars for the selected template in a workspace directory."""
    template_dir = _resolve_template_dir(template_path)
    variable_names = _load_variable_names(template_dir)
    required_vars = _load_required_vars(template_dir)

    candidate_values: dict[str, Any] = {
        "project_name": intent.project_name,
        "region": intent.region,
        "cloud": intent.cloud,
        "use_case": intent.use_case,
        "traffic_tier": intent.traffic_tier,
        "environment": "dev",
    }
    if extra_vars:
        candidate_values.update(extra_vars)

    missing_required = [
        var
        for var in required_vars
        if candidate_values.get(var) in (None, "")
    ]
    if missing_required:
        raise VariableInjectionError(
            "Missing required Terraform variables: " + ", ".join(missing_required)
        )

    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    tfvars_path = workspace / "terraform.tfvars"

    lines = []
    for var_name in variable_names:
        value = candidate_values.get(var_name)
        if value in (None, ""):
            continue
        lines.append(f"{var_name} = {_to_hcl(value)}")

    tfvars_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tfvars_path
