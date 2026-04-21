import tempfile
from pathlib import Path

import pytest

from cloudpilot.jobs import tasks


def test_execute_destroy_job_passes_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = "destroy-session-1"
    workspace = Path(tempfile.gettempdir()) / "cloudpilot" / session_id
    workspace.mkdir(parents=True, exist_ok=True)

    captured: dict = {}

    def fake_run_destroy(workspace_dir, env_vars):
        captured["workspace_dir"] = workspace_dir
        captured["env_vars"] = env_vars
        return "ok"

    statuses: list[dict] = []

    def status_writer(job_id, status, logs=None, output_url=None):
        statuses.append({"job_id": job_id, "status": status, "logs": logs or []})

    monkeypatch.setattr(tasks, "run_destroy", fake_run_destroy)

    result = tasks.execute_destroy_job(
        job_id="job-1",
        session_id=session_id,
        intent_dict={
            "use_case": "static_website",
            "traffic_tier": "low",
            "cloud": "aws",
            "region": "us-east-1",
            "project_name": "demo",
            "raw_input": "",
            "confidence": 1.0,
        },
        credentials_dict={
            "aws": {
                "access_key": "ak",
                "secret_key": "sk",
            }
        },
        status_writer=status_writer,
    )

    assert result["status"] == "SUCCESS"
    assert captured["workspace_dir"] == workspace
    assert captured["env_vars"]["AWS_ACCESS_KEY_ID"] == "ak"
    assert captured["env_vars"]["AWS_SECRET_ACCESS_KEY"] == "sk"
    assert captured["env_vars"]["AWS_DEFAULT_REGION"] == "us-east-1"
    assert statuses[-1]["status"] == "SUCCESS"


def test_execute_destroy_job_requires_known_cloud() -> None:
    with pytest.raises(ValueError, match="No adapter for cloud"):
        tasks.execute_destroy_job(
            job_id="job-2",
            session_id="s2",
            intent_dict={
                "use_case": "static_website",
                "traffic_tier": "low",
                "cloud": "unknown",
                "region": "us-east-1",
                "project_name": "demo",
                "raw_input": "",
                "confidence": 1.0,
            },
            credentials_dict={},
            status_writer=lambda *_args, **_kwargs: None,
        )
