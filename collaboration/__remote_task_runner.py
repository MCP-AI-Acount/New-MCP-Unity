"""
Cloud Run HTTPS 요청 기반 원격 작업 실행 파이프라인
"""

from typing import Any, Dict

from collaboration.__screenshot_to_sheet_pipeline import run_pipeline
from common.__n8n_logger import post_n8n_log


def run_remote_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_type = payload.get("task_type", "")
    request_id = payload.get("request_id", "")

    if task_type == "screenshot_to_sheet":
        result = run_pipeline(
            image_path=payload["image_path"],
            template_path=payload["template_path"],
            spreadsheet_id=payload.get("spreadsheet_id", ""),
            dry_run=bool(payload.get("dry_run", False)),
        )
    else:
        result = {"error": f"지원하지 않는 task_type: {task_type}"}

    log_payload = {
        "source": "cloud_run_remote_task_runner",
        "request_id": request_id,
        "task_type": task_type,
        "result": result,
    }
    log_result = post_n8n_log(log_payload, webhook_url=payload.get("n8n_webhook_url", ""))

    return {
        "ok": "error" not in result,
        "request_id": request_id,
        "task_type": task_type,
        "task_result": result,
        "n8n_log_result": log_result,
    }
