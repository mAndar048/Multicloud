"""Subprocess Terraform execution helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class TerraformError(Exception):
    """Raised when a Terraform command fails."""

    def __init__(self, message: str, *, command: list[str] | None = None) -> None:
        super().__init__(message)
        self.command = command or []


def _templates_root() -> Path:
    return Path(__file__).resolve().parents[1] / "templates"


def _terraform_bin() -> str:
    return os.getenv("TERRAFORM_BIN", "terraform")


def _run_cmd(command: list[str], cwd: Path, env: dict[str, str]) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        binary = command[0] if command else _terraform_bin()
        raise TerraformError(
            "Terraform executable not found. "
            f"Attempted binary '{binary}'. "
            "Install Terraform and ensure it is available on PATH, "
            "or set TERRAFORM_BIN to the full executable path.",
            command=command,
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        message_parts = [
            f"Terraform command failed: {' '.join(command)}",
            f"exit_code={completed.returncode}",
        ]
        if stderr:
            message_parts.append(f"stderr={stderr}")
        elif stdout:
            message_parts.append(f"stdout={stdout}")
        raise TerraformError(" | ".join(message_parts), command=command)

    return completed.stdout or ""


def _prepare_workspace(template_path: str | Path, workspace_dir: str | Path) -> Path:
    source = Path(template_path)
    if not source.is_absolute():
        source = _templates_root() / source
    destination = Path(workspace_dir)

    if not source.exists() or not source.is_dir():
        raise TerraformError(f"Template directory not found: {source}")

    destination.mkdir(parents=True, exist_ok=True)

    for child in source.iterdir():
        target = destination / child.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)

    return destination


def _write_tfvars(tfvars: dict[str, Any] | str | Path | None, workspace: Path) -> Path | None:
    if tfvars is None:
        return None

    destination = workspace / "terraform.tfvars"

    if isinstance(tfvars, dict):
        lines = []
        for key, value in tfvars.items():
            lines.append(f"{key} = {json.dumps(value)}")
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return destination

    tfvars_path = Path(tfvars)
    if not tfvars_path.exists() or not tfvars_path.is_file():
        raise TerraformError(f"tfvars file not found: {tfvars_path}")

    shutil.copy2(tfvars_path, destination)
    return destination


def run_deployment(
    template_path: str | Path,
    workspace_dir: str | Path,
    tfvars: dict[str, Any] | str | Path | None = None,
    cloud_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run terraform init, plan, apply and return terraform output JSON."""
    workspace = _prepare_workspace(template_path, workspace_dir)
    _write_tfvars(tfvars, workspace)

    env = os.environ.copy()
    env.update(cloud_env or {})

    terraform = _terraform_bin()
    init_stdout = _run_cmd([terraform, "init", "-input=false"], workspace, env)
    plan_stdout = _run_cmd(
        [terraform, "plan", "-input=false", "-out", "tfplan"],
        workspace,
        env,
    )
    apply_stdout = _run_cmd(
        [terraform, "apply", "-input=false", "-auto-approve", "tfplan"],
        workspace,
        env,
    )
    output_stdout = _run_cmd([terraform, "output", "-json"], workspace, env)

    try:
        raw_outputs = json.loads(output_stdout) if output_stdout.strip() else {}
        if not isinstance(raw_outputs, dict):
            raise ValueError("Terraform output JSON must be an object.")
    except (json.JSONDecodeError, ValueError) as exc:
        raise TerraformError(
            f"Failed to parse terraform output JSON: {exc}",
            command=[terraform, "output", "-json"],
        ) from exc

    normalized_outputs = {}
    for key, value in raw_outputs.items():
        if isinstance(value, dict) and "value" in value:
            normalized_outputs[key] = value["value"]
        else:
            normalized_outputs[key] = value

    return {
        "workspace": str(workspace),
        "init_stdout": init_stdout,
        "plan_stdout": plan_stdout,
        "apply_stdout": apply_stdout,
        "outputs": normalized_outputs,
    }


def run_destroy(
    workspace_dir: str | Path,
    cloud_env: dict[str, str] | None = None,
) -> str:
    """Run terraform destroy in an existing workspace."""
    workspace = Path(workspace_dir)
    if not workspace.exists() or not workspace.is_dir():
        raise TerraformError(f"Workspace directory not found: {workspace}")

    env = os.environ.copy()
    env.update(cloud_env or {})

    terraform = _terraform_bin()
    _run_cmd([terraform, "init", "-input=false"], workspace, env)
    destroy_stdout = _run_cmd(
        [terraform, "destroy", "-input=false", "-auto-approve"],
        workspace,
        env,
    )
    return destroy_stdout
