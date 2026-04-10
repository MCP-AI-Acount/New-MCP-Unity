#!/usr/bin/env bash
set -euo pipefail

# command: Cloud Run 통해 Unity 그래프 적용 후 스크린샷/로그 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

CLOUD_RUN_URL="${CLOUD_RUN_URL:-}"
REMOTE_API_BEARER_TOKEN="${REMOTE_API_BEARER_TOKEN:-}"
UNITY_WORKER_URL="${UNITY_WORKER_URL:-}"
UNITY_WORKER_BEARER_TOKEN="${UNITY_WORKER_BEARER_TOKEN:-}"
PROJECT_NAME="${PROJECT_NAME:-ReportMaker}"
PROJECT_PATH="${PROJECT_PATH:-}"
SCENE_NAME="${SCENE_NAME:-SampleScene}"
CANVAS_NAME="${CANVAS_NAME:-Canvas}"
GRAPH_NAME="${GRAPH_NAME:-Graph}"
COLOR_HEX="${COLOR_HEX:-#00FF00}"
MAC_REPO_DIR="${MAC_REPO_DIR:-}"
MAC_BRANCH_NAME="${MAC_BRANCH_NAME:-main}"

if [[ -z "$CLOUD_RUN_URL" || -z "$REMOTE_API_BEARER_TOKEN" || -z "$UNITY_WORKER_URL" ]]; then
  echo "[verify_unity_graph] 필수 환경변수 누락" >&2
  echo "  - CLOUD_RUN_URL" >&2
  echo "  - REMOTE_API_BEARER_TOKEN" >&2
  echo "  - UNITY_WORKER_URL" >&2
  exit 1
fi

REQUEST_ID="unity-graph-$(date +%s)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

TASK_RESPONSE_JSON="$TMP_DIR/task_response.json"
SCREENSHOT_RESPONSE_JSON="$TMP_DIR/screenshot_response.json"
SCREENSHOT_FILE="$TMP_DIR/unity-after.png"

task_payload=$(
  python3 - <<PY
import json
print(json.dumps({
  "request_id": "${REQUEST_ID}-style",
  "task_type": "set_canvas_graph_horizontal_green",
  "task_payload": {
    "scene": "${SCENE_NAME}",
    "canvasName": "${CANVAS_NAME}",
    "graphName": "${GRAPH_NAME}",
    "colorHex": "${COLOR_HEX}",
  },
  "project_name": "${PROJECT_NAME}",
  "project_path": "${PROJECT_PATH}",
  "unity_worker_url": "${UNITY_WORKER_URL}",
  "unity_worker_bearer_token": "${UNITY_WORKER_BEARER_TOKEN}",
  "run_async": False
}, ensure_ascii=False))
PY
)

curl -sS -X POST "${CLOUD_RUN_URL%/}/v1/unity/tasks/run" \
  -H "Authorization: Bearer ${REMOTE_API_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$task_payload" > "$TASK_RESPONSE_JSON"

echo "[verify_unity_graph] style task response saved: $TASK_RESPONSE_JSON"
python3 - <<PY
import json
from pathlib import Path
resp = json.loads(Path("${TASK_RESPONSE_JSON}").read_text(encoding="utf-8"))
print(json.dumps(resp, ensure_ascii=False, indent=2))
if not resp.get("ok"):
    raise SystemExit(1)
PY

screenshot_payload=$(
  python3 - <<PY
import json
print(json.dumps({
  "request_id": "${REQUEST_ID}-shot",
  "task_type": "play_and_capture",
  "task_payload": {
    "sceneName": "${SCENE_NAME}",
    "screenshotPath": "/tmp/unity-after-graph.png"
  },
  "project_name": "${PROJECT_NAME}",
  "project_path": "${PROJECT_PATH}",
  "unity_worker_url": "${UNITY_WORKER_URL}",
  "unity_worker_bearer_token": "${UNITY_WORKER_BEARER_TOKEN}",
  "run_async": False
}, ensure_ascii=False))
PY
)

curl -sS -X POST "${CLOUD_RUN_URL%/}/v1/unity/tasks/run" \
  -H "Authorization: Bearer ${REMOTE_API_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$screenshot_payload" > "$SCREENSHOT_RESPONSE_JSON"

echo "[verify_unity_graph] screenshot task response saved: $SCREENSHOT_RESPONSE_JSON"
python3 - <<PY
import json
from pathlib import Path
resp = json.loads(Path("${SCREENSHOT_RESPONSE_JSON}").read_text(encoding="utf-8"))
print(json.dumps(resp, ensure_ascii=False, indent=2))
if not resp.get("ok"):
    raise SystemExit(1)
PY

read_payload=$(
  python3 - <<PY
import json
print(json.dumps({
  "request_id": "${REQUEST_ID}-read",
  "file_path": "/tmp/unity-after-graph.png",
  "project_name": "${PROJECT_NAME}",
  "project_path": "${PROJECT_PATH}",
  "unity_worker_url": "${UNITY_WORKER_URL}",
  "unity_worker_bearer_token": "${UNITY_WORKER_BEARER_TOKEN}",
  "run_async": False
}, ensure_ascii=False))
PY
)

FILE_RESPONSE_JSON="$TMP_DIR/file_response.json"
curl -sS -X POST "${CLOUD_RUN_URL%/}/v1/unity/files/read" \
  -H "Authorization: Bearer ${REMOTE_API_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$read_payload" > "$FILE_RESPONSE_JSON"

python3 - <<PY
import base64
import json
from pathlib import Path
resp = json.loads(Path("${FILE_RESPONSE_JSON}").read_text(encoding="utf-8"))
if not resp.get("ok"):
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    raise SystemExit(1)
content = resp.get("file_bytes_base64", "")
if not content:
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    raise SystemExit(1)
Path("${SCREENSHOT_FILE}").write_bytes(base64.b64decode(content.encode("utf-8")))
print(json.dumps({"saved_screenshot": "${SCREENSHOT_FILE}"}, ensure_ascii=False, indent=2))
PY

echo "[verify_unity_graph] screenshot file: ${SCREENSHOT_FILE}"

if [[ -n "${MAC_HOST:-}" ]]; then
  ssh "${MAC_HOST}" "REPO_DIR='${MAC_REPO_DIR}' BRANCH_NAME='${MAC_BRANCH_NAME}' bash '${MAC_REPO_DIR}/EXE/mac_automation/git_pull_on_wake.sh'" || true
  echo "[verify_unity_graph] mac pull trigger sent via ssh: ${MAC_HOST}"
fi
