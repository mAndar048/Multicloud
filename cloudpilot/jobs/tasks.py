"""Celery task placeholders."""

from cloudpilot.jobs.worker import celery_app


@celery_app.task(name="cloudpilot.deploy_task")
def deploy_task(session_id: str, intent_dict: dict, credentials_dict: dict) -> dict:
    return {
        "session_id": session_id,
        "status": "PENDING",
        "intent": intent_dict,
        "credentials_received": bool(credentials_dict),
    }


@celery_app.task(name="cloudpilot.destroy_task")
def destroy_task(session_id: str) -> dict:
    return {"session_id": session_id, "status": "PENDING"}
