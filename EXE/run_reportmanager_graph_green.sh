#!/usr/bin/env bash
set -euo pipefail

# command: ReportManager SampleScene Canvas/Graph 초록 적용 + 검증 스크린샷
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$REPO_ROOT/rules/.env.local}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${CLOUD_RUN_URL:-}" ]]; then
  if [[ -n "${REMOTE_MCP_GATEWAY_URL:-}" ]]; then
    CLOUD_RUN_URL="$REMOTE_MCP_GATEWAY_URL"
  elif [[ -n "${CLOUD_RUN_GATEWAY_URL:-}" ]]; then
    CLOUD_RUN_URL="$CLOUD_RUN_GATEWAY_URL"
  fi
fi

PROJECT_NAME="${PROJECT_NAME:-ReportManager}"
SCENE_NAME="${SCENE_NAME:-SampleScene}"
CANVAS_NAME="${CANVAS_NAME:-Canvas}"
GRAPH_NAME="${GRAPH_NAME:-Graph}"
COLOR_HEX="${COLOR_HEX:-#00FF00}"

CLOUD_RUN_URL="${CLOUD_RUN_URL:-}"
REMOTE_API_BEARER_TOKEN="${REMOTE_API_BEARER_TOKEN:-}"
UNITY_WORKER_URL="${UNITY_WORKER_URL:-}"
UNITY_WORKER_BEARER_TOKEN="${UNITY_WORKER_BEARER_TOKEN:-}"
PROJECT_PATH="${PROJECT_PATH:-}"
MAC_HOST="${MAC_HOST:-}"
MAC_REPO_DIR="${MAC_REPO_DIR:-}"
MAC_BRANCH_NAME="${MAC_BRANCH_NAME:-main}"

exec bash "$REPO_ROOT/EXE/verify_unity_graph_cloud_apply.sh"
