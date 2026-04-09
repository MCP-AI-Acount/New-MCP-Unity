#!/usr/bin/env python3
"""
Cloud Run 배포용 HTTPS 게이트웨이
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collaboration.remote_task_runner import run_remote_task
from collaboration.unity_remote_orchestrator import dispatch_unity_task

try:
    from google.cloud import tasks_v2
    from google.protobuf import timestamp_pb2
except Exception:
    tasks_v2 = None
    timestamp_pb2 = None

app = FastAPI(title="remote-mcp-gateway", version="1.0.0")


class TaskRequest(BaseModel):
    request_id: str = ""
    task_type: str
    image_path: str = ""
    template_path: str = ""
    spreadsheet_id: str = ""
    dry_run: bool = False
    n8n_webhook_url: str = ""
    run_async: bool = True
    delay_seconds: int = 0


class UnityTaskRequest(BaseModel):
    request_id: str = ""
    task_type: str
    task_payload: Dict[str, Any] = {}
    project_name: str = ""
    project_path: str = ""
    unity_worker_url: str = ""
    n8n_webhook_url: str = ""
    run_async: bool = True
    delay_seconds: int = 0


def _check_bearer(auth_header: str) -> None:
    required_token = os.environ.get("REMOTE_API_BEARER_TOKEN", "")
    if not required_token:
        return
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다.")
    provided = auth_header[len("Bearer ") :].strip()
    if provided != required_token:
        raise HTTPException(status_code=401, detail="Bearer 토큰이 올바르지 않습니다.")


def _check_internal_request(x_cloud_tasks_token: str, x_cloudtasks_taskname: str) -> None:
    required_token = os.environ.get("CLOUD_TASKS_INTERNAL_TOKEN", "")
    if required_token:
        if x_cloud_tasks_token != required_token:
            raise HTTPException(status_code=401, detail="내부 작업 토큰이 올바르지 않습니다.")
        return
    if not x_cloudtasks_taskname:
        raise HTTPException(status_code=401, detail="내부 작업 엔드포인트는 Cloud Tasks 호출만 허용합니다.")


def _cloud_tasks_project_id() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or os.environ.get("PROJECT_ID")
        or ""
    )


def _cloud_tasks_location() -> str:
    return (
        os.environ.get("CLOUD_TASKS_LOCATION")
        or os.environ.get("REGION")
        or os.environ.get("GCP_REGION")
        or "asia-northeast3"
    )


def _base_url_from_request(req: Request) -> str:
    configured = os.environ.get("CLOUD_RUN_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    proto = req.headers.get("x-forwarded-proto", req.url.scheme)
    host = req.headers.get("host", req.url.netloc)
    if not host:
        raise HTTPException(status_code=500, detail="요청 host 정보를 확인할 수 없습니다.")
    return f"{proto}://{host}".rstrip("/")


def _normalize_delay(delay_seconds: int) -> int:
    if delay_seconds < 0:
        return 0
    if delay_seconds > 3600:
        return 3600
    return delay_seconds


def _enqueue_http_task(
    req: Request,
    queue_name: str,
    handler_path: str,
    payload: Dict[str, Any],
    delay_seconds: int = 0,
) -> str:
    if tasks_v2 is None:
        raise HTTPException(status_code=500, detail="google-cloud-tasks 패키지가 필요합니다.")
    project_id = _cloud_tasks_project_id()
    if not project_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_PROJECT 설정이 필요합니다.")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(project_id, _cloud_tasks_location(), queue_name)
    target_url = _base_url_from_request(req) + handler_path

    headers = {"Content-Type": "application/json"}
    internal_token = os.environ.get("CLOUD_TASKS_INTERNAL_TOKEN", "")
    if internal_token:
        headers["X-Cloud-Tasks-Token"] = internal_token

    task: Dict[str, Any] = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": target_url,
            "headers": headers,
            "body": json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        }
    }

    normalized_delay = _normalize_delay(delay_seconds)
    if normalized_delay > 0:
        if timestamp_pb2 is None:
            raise HTTPException(status_code=500, detail="google protobuf 패키지가 필요합니다.")
        ts = timestamp_pb2.Timestamp()
        ts.FromDatetime(datetime.now(timezone.utc) + timedelta(seconds=normalized_delay))
        task["schedule_time"] = ts

    created = client.create_task(parent=parent, task=task)
    return created.name


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "remote-mcp-gateway"}


@app.post("/v1/tasks/run")
def run_task(body: TaskRequest, req: Request, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    payload = body.model_dump()
    request_id = payload.get("request_id", "") or str(uuid.uuid4())
    payload["request_id"] = request_id

    if body.run_async:
        queue_name = os.environ.get("CLOUD_TASKS_QUEUE_REMOTE", "remote-mcp-tasks")
        task_name = _enqueue_http_task(
            req=req,
            queue_name=queue_name,
            handler_path="/internal/tasks/execute",
            payload=payload,
            delay_seconds=body.delay_seconds,
        )
        return {
            "ok": True,
            "accepted": True,
            "mode": "async_queue",
            "request_id": request_id,
            "cloud_task_name": task_name,
        }

    payload["run_async"] = False
    return run_remote_task(payload)


@app.post("/v1/unity/tasks/run")
def run_unity_task(body: UnityTaskRequest, req: Request, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    payload = body.model_dump()
    request_id = payload.get("request_id", "") or str(uuid.uuid4())
    payload["request_id"] = request_id

    if body.run_async:
        queue_name = os.environ.get("CLOUD_TASKS_QUEUE_UNITY", "remote-mcp-unity-tasks")
        task_name = _enqueue_http_task(
            req=req,
            queue_name=queue_name,
            handler_path="/internal/unity/tasks/execute",
            payload=payload,
            delay_seconds=body.delay_seconds,
        )
        return {
            "ok": True,
            "accepted": True,
            "mode": "async_queue",
            "request_id": request_id,
            "cloud_task_name": task_name,
        }

    payload["run_async"] = False
    return dispatch_unity_task(payload)


@app.post("/internal/tasks/execute")
def execute_internal_task(
    body: TaskRequest,
    x_cloud_tasks_token: str = Header(default=""),
    x_cloudtasks_taskname: str = Header(default=""),
) -> Dict[str, Any]:
    _check_internal_request(x_cloud_tasks_token, x_cloudtasks_taskname)
    payload = body.model_dump()
    payload["run_async"] = False
    result = run_remote_task(payload)
    return {
        "ok": bool(result.get("ok")),
        "cloud_task_name": x_cloudtasks_taskname,
        "result": result,
    }


@app.post("/internal/unity/tasks/execute")
def execute_internal_unity_task(
    body: UnityTaskRequest,
    x_cloud_tasks_token: str = Header(default=""),
    x_cloudtasks_taskname: str = Header(default=""),
) -> Dict[str, Any]:
    _check_internal_request(x_cloud_tasks_token, x_cloudtasks_taskname)
    payload = body.model_dump()
    payload["run_async"] = False
    result = dispatch_unity_task(payload)
    return {
        "ok": bool(result.get("ok")),
        "cloud_task_name": x_cloudtasks_taskname,
        "result": result,
    }
