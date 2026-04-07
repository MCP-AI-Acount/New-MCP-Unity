#!/usr/bin/env python3
"""
Cloud Run 배포용 HTTPS 게이트웨이
"""

import os
import sys
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collaboration.remote_task_runner import run_remote_task
from collaboration.unity_remote_orchestrator import dispatch_unity_task

app = FastAPI(title="remote-mcp-gateway", version="1.0.0")


class TaskRequest(BaseModel):
    request_id: str = ""
    task_type: str
    image_path: str = ""
    template_path: str = ""
    spreadsheet_id: str = ""
    dry_run: bool = False
    n8n_webhook_url: str = ""


class UnityTaskRequest(BaseModel):
    request_id: str = ""
    task_type: str
    task_payload: Dict[str, Any] = {}
    project_name: str = ""
    project_path: str = ""
    unity_worker_url: str = ""
    n8n_webhook_url: str = ""


def _check_bearer(auth_header: str) -> None:
    required_token = os.environ.get("REMOTE_API_BEARER_TOKEN", "")
    if not required_token:
        return
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다.")
    provided = auth_header[len("Bearer ") :].strip()
    if provided != required_token:
        raise HTTPException(status_code=401, detail="Bearer 토큰이 올바르지 않습니다.")


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "remote-mcp-gateway"}


@app.post("/v1/tasks/run")
def run_task(body: TaskRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    payload = body.model_dump()
    return run_remote_task(payload)


@app.post("/v1/unity/tasks/run")
def run_unity_task(body: UnityTaskRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    payload = body.model_dump()
    return dispatch_unity_task(payload)
