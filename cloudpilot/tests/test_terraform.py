import subprocess

import pytest

from cloudpilot.engine import terraform_runner
from cloudpilot.engine.terraform_runner import TerraformError


def _create_template_dir(path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "main.tf").write_text("terraform {}\n", encoding="utf-8")
    (path / "variables.tf").write_text("variable \"project_name\" { type = string }\n", encoding="utf-8")
    (path / "outputs.tf").write_text("output \"endpoint_url\" { value = \"ok\" }\n", encoding="utf-8")
    (path / "meta.yaml").write_text("name: test\n", encoding="utf-8")


def test_run_deployment_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    template = tmp_path / "template"
    workspace = tmp_path / "workspace"
    _create_template_dir(template)

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        subcommand = command[1]
        if subcommand == "output":
            return subprocess.CompletedProcess(
                command,
                0,
                '{"endpoint_url": {"value": "https://demo"}, "resource_id": {"value": "abc"}}',
                "",
            )
        return subprocess.CompletedProcess(command, 0, f"{subcommand} ok", "")

    monkeypatch.setattr(terraform_runner.subprocess, "run", fake_run)

    result = terraform_runner.run_deployment(
        template_path=template,
        workspace_dir=workspace,
        tfvars={"project_name": "demo"},
        cloud_env={"AWS_DEFAULT_REGION": "us-east-1"},
    )

    assert calls[0][1] == "init"
    assert calls[1][1] == "plan"
    assert calls[2][1] == "apply"
    assert calls[3][1] == "output"
    assert result["outputs"]["endpoint_url"] == "https://demo"
    assert result["outputs"]["resource_id"] == "abc"
    assert (workspace / "terraform.tfvars").exists()


def test_run_deployment_raises_clean_error_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = tmp_path / "template"
    workspace = tmp_path / "workspace"
    _create_template_dir(template)

    def fake_run(command, **kwargs):
        if command[1] == "plan":
            return subprocess.CompletedProcess(command, 1, "", "plan failure")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(terraform_runner.subprocess, "run", fake_run)

    with pytest.raises(TerraformError, match="plan failure"):
        terraform_runner.run_deployment(template, workspace)


def test_run_deployment_raises_on_invalid_output_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = tmp_path / "template"
    workspace = tmp_path / "workspace"
    _create_template_dir(template)

    def fake_run(command, **kwargs):
        if command[1] == "output":
            return subprocess.CompletedProcess(command, 0, "not-json", "")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(terraform_runner.subprocess, "run", fake_run)

    with pytest.raises(TerraformError, match="Failed to parse terraform output JSON"):
        terraform_runner.run_deployment(template, workspace)


def test_run_destroy_executes_destroy(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "main.tf").write_text("terraform {}\n", encoding="utf-8")

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(terraform_runner.subprocess, "run", fake_run)

    terraform_runner.run_destroy(workspace)

    assert calls[0][1] == "init"
    assert calls[1][1] == "destroy"


def test_run_deployment_reports_missing_terraform_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    template = tmp_path / "template"
    workspace = tmp_path / "workspace"
    _create_template_dir(template)

    def fake_run(command, **kwargs):
        raise FileNotFoundError("terraform not found")

    monkeypatch.setattr(terraform_runner.subprocess, "run", fake_run)

    with pytest.raises(TerraformError, match="Terraform executable not found"):
        terraform_runner.run_deployment(template, workspace)
