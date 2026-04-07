#!/usr/bin/env python3
# 사용자 실행 예시 (주석)
# curl -X POST "https://<cloud-run-url>/v1/tasks/run" \
#   -H "Authorization: Bearer <REMOTE_API_BEARER_TOKEN>" \
#   -H "Content-Type: application/json" \
#   -d '{"request_id":"req-1","task_type":"screenshot_to_sheet","image_path":"temp/capture.png","template_path":"rules/sheets_ocr_template.example.json","spreadsheet_id":"<id>","dry_run":false}'

import argparse
import json
from urllib import request


def main():
    parser = argparse.ArgumentParser(description="Cloud Run 원격 작업 실행")
    parser.add_argument("--url", required=True, help="Cloud Run 서비스 URL")
    parser.add_argument("--bearer-token", default="", help="Bearer 토큰")
    parser.add_argument("--payload-json", required=True, help="요청 payload JSON 문자열")
    args = parser.parse_args()

    payload = args.payload_json.encode("utf-8")
    req = request.Request(
        url=args.url.rstrip("/") + "/v1/tasks/run",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.bearer_token}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        print(json.dumps(json.loads(resp.read().decode("utf-8")), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
