"""
Cloud Run -> Unity Worker(HTTPS) 작업 전달 오케스트레이터
"""

import json
import os
import base64
from typing import Any, Dict
from urllib import error, request

from common.n8n_logger import post_n8n_log


def _post_json(
    url: str,
    payload: Dict[str, Any],
    timeout_sec: int = 30,
    headers: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    req = request.Request(
        url=url,
        data=data,
        headers=request_headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(body) if body else {}
            except Exception:
                parsed = {"raw": body[:2000]}
            return {"ok": True, "status": resp.status, "body": parsed}
    except error.HTTPError as e:
        return {
            "ok": False,
            "status": e.code,
            "body": e.read().decode("utf-8", errors="ignore")[:2000],
        }
    except Exception as e:
        return {"ok": False, "status": 0, "body": str(e)}


def dispatch_unity_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    worker_url = payload.get("unity_worker_url") or os.environ.get("UNITY_WORKER_URL", "")
    if not worker_url:
        return {"ok": False, "error": "UNITY_WORKER_URL 이 필요합니다."}

    worker_bearer_token = payload.get("unity_worker_bearer_token") or os.environ.get("UNITY_WORKER_BEARER_TOKEN", "")
    worker_headers: Dict[str, str] = {}
    if worker_bearer_token:
        worker_headers["Authorization"] = f"Bearer {worker_bearer_token}"

    worker_payload = {
        "request_id": payload.get("request_id", ""),
        "task_type": payload.get("task_type", ""),
        "task_payload": payload.get("task_payload", {}),
        "project_name": payload.get("project_name", ""),
        "project_path": payload.get("project_path", ""),
    }
    worker_result = _post_json(
        worker_url.rstrip("/") + "/v1/unity/execute",
        worker_payload,
        timeout_sec=120,
        headers=worker_headers,
    )

    log_result = post_n8n_log(
        {
            "source": "unity_remote_orchestrator",
            "request_id": payload.get("request_id", ""),
            "task_type": payload.get("task_type", ""),
            "worker_result": worker_result,
        },
        webhook_url=payload.get("n8n_webhook_url", ""),
    )
    worker_ok = bool(worker_result.get("ok"))
    worker_body = worker_result.get("body", {})
    unity_result = worker_body.get("result", {}) if isinstance(worker_body, dict) else {}
    unity_returncode = int(unity_result.get("returncode", 1) or 1)
    unity_ok = worker_ok and unity_returncode == 0 and bool(unity_result.get("ok", False))
    return {
        "ok": unity_ok,
        "worker_result": worker_result,
        "n8n_log_result": log_result,
    }


def read_unity_worker_file(payload: Dict[str, Any]) -> Dict[str, Any]:
    worker_url = payload.get("unity_worker_url") or os.environ.get("UNITY_WORKER_URL", "")
    if not worker_url:
        return {"ok": False, "error": "UNITY_WORKER_URL 이 필요합니다."}

    file_path = payload.get("file_path", "")
    if not file_path:
        return {"ok": False, "error": "file_path 가 필요합니다."}

    worker_bearer_token = payload.get("unity_worker_bearer_token") or os.environ.get("UNITY_WORKER_BEARER_TOKEN", "")
    worker_headers: Dict[str, str] = {}
    if worker_bearer_token:
        worker_headers["Authorization"] = f"Bearer {worker_bearer_token}"

    worker_payload = {
        "request_id": payload.get("request_id", ""),
        "file_path": file_path,
        "project_name": payload.get("project_name", ""),
        "project_path": payload.get("project_path", ""),
    }
    worker_result = _post_json(
        worker_url.rstrip("/") + "/v1/files/read",
        worker_payload,
        timeout_sec=60,
        headers=worker_headers,
    )
    if not worker_result.get("ok"):
        return {
            "ok": False,
            "worker_result": worker_result,
        }

    body = worker_result.get("body", {})
    content_b64 = body.get("content_base64", "")
    if not content_b64:
        return {
            "ok": False,
            "error": "worker 응답에 content_base64 가 없습니다.",
            "worker_result": worker_result,
        }

    try:
        decoded = base64.b64decode(content_b64.encode("utf-8"))
    except Exception as e:
        return {
            "ok": False,
            "error": f"base64 decode 실패: {e}",
            "worker_result": worker_result,
        }

    return {
        "ok": True,
        "worker_result": worker_result,
        "file_bytes_base64": content_b64,
        "file_size_bytes": len(decoded),
    }
