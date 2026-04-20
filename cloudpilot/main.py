"""FastAPI entry point for CloudPilot."""

from fastapi import FastAPI

app = FastAPI(title="CloudPilot", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
