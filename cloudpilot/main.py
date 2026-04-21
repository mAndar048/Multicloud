"""FastAPI entry point for CloudPilot."""

import json
import socket
import threading
import uuid
from typing import Any, Optional

import redis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cloudpilot.conversation.state_machine import ConversationSession
from cloudpilot.intent.parser import parse

load_dotenv()


class SessionStartRequest(BaseModel):
    initial_input: str
    credentials: dict[str, Any]


class SessionAnswerRequest(BaseModel):
    answer: str


app = FastAPI(title="CloudPilot", version="0.1.0")

# In-memory session store (MVP)
session_store: dict[str, dict[str, Any]] = {}
local_job_store: dict[str, dict[str, Any]] = {}
local_job_store_lock = threading.Lock()


def _is_redis_available(host: str = "localhost", port: int = 6379, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _update_local_job_status(
    job_id: str,
    status: str,
    logs: list[str] | None = None,
    output_url: str | None = None,
) -> None:
    data: dict[str, Any] = {"status": status, "logs": list(logs or [])}
    if output_url is not None:
        data["output_url"] = output_url

    with local_job_store_lock:
        local_job_store[job_id] = data


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session/start")
def start_session(request: SessionStartRequest) -> dict[str, Any]:
    """Start a new conversation session."""
    session_id = str(uuid.uuid4())

    # Parse initial intent
    intent = parse(request.initial_input)

    # Create conversation session
    session = ConversationSession(session_id, intent)

    # Store session and credentials
    session_store[session_id] = {
        "session": session,
        "credentials": request.credentials,
    }

    # Get first question
    question = session.next_question()
    if question:
        return {"session_id": session_id, "question": question}
    else:
        return {"session_id": session_id, "ready": True}


@app.post("/session/{session_id}/answer")
def answer_question(session_id: str, request: SessionAnswerRequest) -> dict[str, Any]:
    """Answer the current question in the session."""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_store[session_id]["session"]
    session.answer(request.answer)

    if session.is_ready():
        return {"ready": True}
    else:
        question = session.next_question()
        return {"question": question, "ready": False}


@app.post("/session/{session_id}/deploy")
def deploy_session(session_id: str) -> dict[str, str]:
    """Deploy the infrastructure for the session."""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_store[session_id]["session"]
    if not session.is_ready():
        raise HTTPException(status_code=400, detail="Session not ready for deployment")

    credentials = session_store[session_id]["credentials"]
    intent_dict = session.intent.__dict__

    if _is_redis_available():
        # Lazy import to avoid blocking on Celery connection during startup
        try:
            from cloudpilot.jobs.tasks import deploy_task

            task = deploy_task.delay(session_id, intent_dict, credentials)
            return {"job_id": task.id}
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to start deployment job: {str(e)}. Ensure Celery and Redis are running."
            )

    from cloudpilot.jobs.tasks import execute_deploy_job

    job_id = str(uuid.uuid4())
    _update_local_job_status(job_id, "PENDING", [])
    thread = threading.Thread(
        target=execute_deploy_job,
        kwargs={
            "job_id": job_id,
            "session_id": session_id,
            "intent_dict": intent_dict,
            "credentials_dict": credentials,
            "status_writer": _update_local_job_status,
        },
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.post("/session/{session_id}/destroy")
def destroy_session(session_id: str) -> dict[str, str]:
    """Destroy the infrastructure for the session."""
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")

    if _is_redis_available():
        # Lazy import to avoid blocking on Celery connection during startup
        try:
            from cloudpilot.jobs.tasks import destroy_task

            task = destroy_task.delay(session_id)
            return {"job_id": task.id}
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to start destroy job: {str(e)}. Ensure Celery and Redis are running."
            )

    from cloudpilot.jobs.tasks import execute_destroy_job

    job_id = str(uuid.uuid4())
    _update_local_job_status(job_id, "PENDING", [])
    thread = threading.Thread(
        target=execute_destroy_job,
        kwargs={
            "job_id": job_id,
            "session_id": session_id,
            "status_writer": _update_local_job_status,
        },
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/job/{job_id}/status")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a job."""
    with local_job_store_lock:
        local_job = local_job_store.get(job_id)
    if local_job:
        return local_job

    if not _is_redis_available():
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        r = redis.Redis(host="localhost", port=6379, db=0)
        data = r.get(f"job:{job_id}")
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to read job status: {exc}") from exc

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    return json.loads(data)
