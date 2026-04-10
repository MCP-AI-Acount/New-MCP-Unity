"""
n8n webhook 로 작업 로그 전송
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict
from urllib import error, request


def post_n8n_log(payload: Dict[str, Any], webhook_url: str = "") -> Dict[str, Any]:
    url = webhook_url or os.environ.get("N8N_WEBHOOK_URL", "")
    if not url:
        return {"success": False, "message": "N8N_WEBHOOK_URL 이 비어 있습니다."}

    body = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            response_body = resp.read().decode("utf-8", errors="ignore")
            return {
                "success": True,
                "status": resp.status,
                "response": response_body[:2000],
            }
    except error.HTTPError as e:
        return {
            "success": False,
            "status": e.code,
            "message": e.read().decode("utf-8", errors="ignore")[:2000],
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
