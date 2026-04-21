"""Celery tasks for deployment jobs."""

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

import redis

from cloudpilot.adapters.registry import ADAPTER_REGISTRY
from cloudpilot.engine.template_selector import select_template
from cloudpilot.engine.terraform_runner import run_deployment, run_destroy
from cloudpilot.intent.schema import IntentObject
from cloudpilot.jobs.worker import app


def _get_redis() -> redis.Redis:
    return redis.Redis(host="localhost", port=6379, db=0)


def _update_job_status(job_id: str, status: str, logs: list[str] | None = None, output_url: str | None = None) -> None:
    r = _get_redis()
    data = {"status": status}
    if logs:
        data["logs"] = logs
    if output_url:
        data["output_url"] = output_url
    r.setex(f"job:{job_id}", 86400, json.dumps(data))  # 24h TTL


def _resolve_provider_credentials(
    intent: IntentObject,
    credentials_dict: dict[str, Any],
) -> dict[str, Any]:
    """Normalize UI credential payloads into adapter-specific shapes."""
    if intent.cloud == "aws":
        aws_credentials = dict(credentials_dict.get("aws", {}))
        aws_credentials.setdefault("region", intent.region)
        return aws_credentials

    if intent.cloud == "gcp":
        gcp_credentials = dict(credentials_dict.get("gcp", {}))
        # Keep the raw JSON available for future adapter expansion.
        return gcp_credentials

    if intent.cloud == "digitalocean":
        do_credentials = dict(credentials_dict.get("digitalocean", {}))
        if "token" not in do_credentials and do_credentials.get("api_token"):
            do_credentials["token"] = do_credentials["api_token"]
        return do_credentials

    return credentials_dict


def execute_deploy_job(
    job_id: str,
    session_id: str,
    intent_dict: dict[str, Any],
    credentials_dict: dict[str, Any],
    status_writer: Callable[[str, str, list[str] | None, str | None], None] = _update_job_status,
) -> dict[str, Any]:
    """Run a deployment job with either Redis-backed or local status updates."""
    logs: list[str] = []

    try:
        status_writer(job_id, "RUNNING", logs, None)

        # Reconstruct IntentObject
        intent = IntentObject(**intent_dict)

        # Get adapter
        adapter_class = ADAPTER_REGISTRY.get(intent.cloud)
        if not adapter_class:
            raise ValueError(f"No adapter for cloud: {intent.cloud}")
        adapter = adapter_class()
        provider_credentials = _resolve_provider_credentials(intent, credentials_dict)
        env_vars = adapter.get_env_vars(provider_credentials)

        # Select template
        template_path = select_template(intent)
        logs.append(f"Selected template: {template_path}")

        # Create workspace
        workspace_dir = Path(tempfile.gettempdir()) / "cloudpilot" / session_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Inject variables
        tfvars = {
            "project_name": intent.project_name,
            "region": intent.region,
            "cloud": intent.cloud,
            "use_case": intent.use_case,
            "traffic_tier": intent.traffic_tier,
            "environment": "dev",
        }
        logs.append("Prepared tfvars")

        # Run deployment
        result = run_deployment(template_path, workspace_dir, tfvars, env_vars)
        logs.extend([
            "Terraform init completed",
            "Terraform plan completed",
            "Terraform apply completed",
        ])

        output_url = result["outputs"].get("endpoint_url", "N/A")
        logs.append(f"Deployment successful. Output URL: {output_url}")

        status_writer(job_id, "SUCCESS", logs, output_url)

        return {
            "job_id": job_id,
            "status": "SUCCESS",
            "output_url": output_url,
            "logs": logs,
        }

    except Exception as e:
        error_msg = f"Deployment failed: {str(e)}"
        logs.append(error_msg)
        status_writer(job_id, "FAILED", logs, None)
        raise


def execute_destroy_job(
    job_id: str,
    session_id: str,
    status_writer: Callable[[str, str, list[str] | None, str | None], None] = _update_job_status,
) -> dict[str, Any]:
    """Run a destroy job with either Redis-backed or local status updates."""
    logs: list[str] = []

    try:
        status_writer(job_id, "RUNNING", logs, None)

        # For destroy, we need to know the workspace and credentials
        # This is simplified; in real impl, store workspace path and creds per session
        workspace_dir = Path(tempfile.gettempdir()) / "cloudpilot" / session_id

        if not workspace_dir.exists():
            raise ValueError(f"Workspace not found for session: {session_id}")

        # Assume credentials are stored or passed; for now, empty
        env_vars = {}

        run_destroy(workspace_dir, env_vars)
        logs.append("Terraform destroy completed")

        status_writer(job_id, "SUCCESS", logs, None)

        return {
            "job_id": job_id,
            "status": "SUCCESS",
            "logs": logs,
        }

    except Exception as e:
        error_msg = f"Destroy failed: {str(e)}"
        logs.append(error_msg)
        status_writer(job_id, "FAILED", logs, None)
        raise


@app.task(bind=True, name="cloudpilot.deploy_task")
def deploy_task(self, session_id: str, intent_dict: dict[str, Any], credentials_dict: dict[str, Any]) -> dict[str, Any]:
    return execute_deploy_job(
        self.request.id,
        session_id,
        intent_dict,
        credentials_dict,
        _update_job_status,
    )


@app.task(bind=True, name="cloudpilot.destroy_task")
def destroy_task(self, session_id: str) -> dict[str, Any]:
    return execute_destroy_job(
        self.request.id,
        session_id,
        _update_job_status,
    )
