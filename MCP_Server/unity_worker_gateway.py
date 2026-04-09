#!/usr/bin/env python3
"""
GCP VM 상에서 실행하는 Unity Worker HTTPS 게이트웨이
"""

import os
import subprocess
import base64
from typing import Any, Dict

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from common.unity_project_registry import load_registry, resolve_project_path, set_project

app = FastAPI(title="unity-worker-gateway", version="1.0.0")


class UnityExecuteRequest(BaseModel):
    request_id: str = ""
    task_type: str
    task_payload: Dict[str, Any] = {}
    project_name: str = ""
    project_path: str = ""


class UnityProjectRequest(BaseModel):
    project_name: str
    project_path: str = ""
    set_active: bool = True


class UnityFileReadRequest(BaseModel):
    request_id: str = ""
    file_path: str
    project_name: str = ""
    project_path: str = ""


def _check_bearer(auth_header: str) -> None:
    required_token = os.environ.get("UNITY_WORKER_BEARER_TOKEN", "")
    if not required_token:
        return
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 헤더가 필요합니다.")
    provided = auth_header[len("Bearer ") :].strip()
    if provided != required_token:
        raise HTTPException(status_code=401, detail="Bearer 토큰이 올바르지 않습니다.")


def _run_unity_batch(
    task_type: str,
    task_payload: Dict[str, Any],
    project_name: str = "",
    project_path: str = "",
) -> Dict[str, Any]:
    unity_path = os.environ.get("UNITY_PATH", "/Applications/Unity/Hub/Editor/6000.4.1f1/Unity.app/Contents/MacOS/Unity")
    resolved_project_path = resolve_project_path(project_name=project_name, project_path=project_path)
    if not resolved_project_path:
        resolved_project_path = os.environ.get("UNITY_PROJECT_PATH", "")
    log_path = os.environ.get("UNITY_LOG_PATH", "/tmp/unity-batch.log")
    method_name = os.environ.get("UNITY_BATCH_METHOD", "RemoteAutomation.EntryPoint")

    if not resolved_project_path:
        return {"ok": False, "error": "UNITY_PROJECT_PATH 환경변수 또는 project_name/project_path가 필요합니다."}

    task_json = str(task_payload).replace("'", '"')
    cmd = [
        unity_path,
        "-batchmode",
        "-nographics",
        "-quit",
        "-projectPath",
        resolved_project_path,
        "-executeMethod",
        method_name,
        f"--taskType={task_type}",
        f"--taskPayload={task_json}",
        "-logFile",
        log_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-3000:],
        "stderr": proc.stderr[-3000:],
        "log_path": log_path,
        "project_path": resolved_project_path,
    }


def _create_unity_project(project_name: str, project_path: str = "") -> Dict[str, Any]:
    unity_path = os.environ.get("UNITY_PATH", "/Applications/Unity/Hub/Editor/6000.4.1f1/Unity.app/Contents/MacOS/Unity")
    base_dir = os.environ.get("UNITY_PROJECTS_BASE_DIR", "/Users/Windows/Documents/Task")
    if not project_path:
        project_path = os.path.join(base_dir, project_name)
    os.makedirs(os.path.dirname(project_path), exist_ok=True)

    cmd = [
        unity_path,
        "-batchmode",
        "-nographics",
        "-quit",
        "-createProject",
        project_path,
        "-logFile",
        os.environ.get("UNITY_CREATE_PROJECT_LOG_PATH", "/tmp/unity-create-project.log"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "project_name": project_name,
        "project_path": project_path,
        "stdout": proc.stdout[-3000:],
        "stderr": proc.stderr[-3000:],
    }


def _read_file_base64(file_path: str, project_name: str = "", project_path: str = "") -> Dict[str, Any]:
    resolved_project_path = resolve_project_path(project_name=project_name, project_path=project_path)
    if not resolved_project_path:
        resolved_project_path = os.environ.get("UNITY_PROJECT_PATH", "")

    if os.path.isabs(file_path):
        resolved_file_path = file_path
    else:
        if not resolved_project_path:
            return {"ok": False, "error": "상대 경로 사용 시 UNITY_PROJECT_PATH 또는 project_name/project_path가 필요합니다."}
        resolved_file_path = os.path.join(resolved_project_path, file_path)

    if not os.path.isfile(resolved_file_path):
        return {"ok": False, "error": f"파일을 찾을 수 없습니다: {resolved_file_path}"}

    with open(resolved_file_path, "rb") as f:
        raw = f.read()

    return {
        "ok": True,
        "file_path": resolved_file_path,
        "size_bytes": len(raw),
        "content_base64": base64.b64encode(raw).decode("utf-8"),
    }


@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    return {"ok": True, "service": "unity-worker-gateway"}


@app.post("/v1/unity/execute")
def execute_unity_task(body: UnityExecuteRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    result = _run_unity_batch(
        body.task_type,
        body.task_payload,
        project_name=body.project_name,
        project_path=body.project_path,
    )
    return {
        "ok": bool(result.get("ok")),
        "request_id": body.request_id,
        "task_type": body.task_type,
        "result": result,
    }


@app.get("/v1/projects")
def list_projects(authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    return {"ok": True, "registry": load_registry()}


@app.post("/v1/projects/create")
def create_project(body: UnityProjectRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    create_result = _create_unity_project(body.project_name, body.project_path)
    if not create_result.get("ok"):
        return {"ok": False, "create_result": create_result}
    registry = set_project(
        project_name=body.project_name,
        project_path=create_result["project_path"],
        set_active=body.set_active,
    )
    return {"ok": True, "create_result": create_result, "registry": registry}


@app.post("/v1/projects/set-active")
def set_active_project(body: UnityProjectRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    if not body.project_path:
        existing = resolve_project_path(project_name=body.project_name)
        if not existing:
            return {"ok": False, "error": "등록되지 않은 project_name 입니다. project_path를 함께 전달하세요."}
        project_path = existing
    else:
        project_path = body.project_path
    registry = set_project(
        project_name=body.project_name,
        project_path=project_path,
        set_active=True,
    )
    return {"ok": True, "registry": registry}


@app.post("/v1/files/read")
def read_file(body: UnityFileReadRequest, authorization: str = Header(default="")) -> Dict[str, Any]:
    _check_bearer(authorization)
    result = _read_file_base64(
        file_path=body.file_path,
        project_name=body.project_name,
        project_path=body.project_path,
    )
    return {
        "ok": bool(result.get("ok")),
        "request_id": body.request_id,
        "result": result,
    }
