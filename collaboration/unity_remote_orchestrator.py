"""
Cloud Run -> Unity Worker(HTTPS) 작업 전달 오케스트레이터
"""

import json
import os
from typing import Any, Dict
from urllib import error, request

from common.n8n_logger import post_n8n_log


def _post_json(url: str, payload: Dict[str, Any], timeout_sec: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
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

    worker_payload = {
        "request_id": payload.get("request_id", ""),
        "task_type": payload.get("task_type", ""),
        "task_payload": payload.get("task_payload", {}),
        "project_name": payload.get("project_name", ""),
        "project_path": payload.get("project_path", ""),
    }
    worker_result = _post_json(worker_url.rstrip("/") + "/v1/unity/execute", worker_payload, timeout_sec=120)

    log_result = post_n8n_log(
        {
            "source": "unity_remote_orchestrator",
            "request_id": payload.get("request_id", ""),
            "task_type": payload.get("task_type", ""),
            "worker_result": worker_result,
        },
        webhook_url=payload.get("n8n_webhook_url", ""),
    )
    return {
        "ok": bool(worker_result.get("ok")),
        "worker_result": worker_result,
        "n8n_log_result": log_result,
    }
