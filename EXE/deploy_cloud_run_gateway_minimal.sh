#!/usr/bin/env bash
set -euo pipefail

# command: Cloud Run 게이트웨이 최소 파일만 빌드/배포
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-remote-mcp-gateway}"
REPO_NAME="${REPO_NAME:-remote-mcp-repo}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"

CLOUD_TASKS_QUEUE_REMOTE="${CLOUD_TASKS_QUEUE_REMOTE:-remote-mcp-tasks}"
CLOUD_TASKS_QUEUE_UNITY="${CLOUD_TASKS_QUEUE_UNITY:-remote-mcp-unity-tasks}"
CLOUD_TASKS_INTERNAL_TOKEN="${CLOUD_TASKS_INTERNAL_TOKEN:-}"
EXTRA_ENV_VARS="${EXTRA_ENV_VARS:-}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-false}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID 환경변수가 필요합니다."
  exit 1
fi

if [[ -z "$CLOUD_TASKS_INTERNAL_TOKEN" ]]; then
  CLOUD_TASKS_INTERNAL_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
fi

gcloud config set project "$PROJECT_ID" >/dev/null

if ! gcloud artifacts repositories describe "$REPO_NAME" --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION"
fi

BUILD_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

mkdir -p "$BUILD_DIR/MCP_Server" "$BUILD_DIR/collaboration" "$BUILD_DIR/common"
cp -R "$REPO_ROOT/MCP_Server/." "$BUILD_DIR/MCP_Server/"
cp -R "$REPO_ROOT/collaboration/." "$BUILD_DIR/collaboration/"
cp -R "$REPO_ROOT/common/." "$BUILD_DIR/common/"

cat > "$BUILD_DIR/Dockerfile" <<'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

COPY MCP_Server/requirements-cloudrun.txt /app/requirements-cloudrun.txt
RUN pip install --no-cache-dir -r /app/requirements-cloudrun.txt

COPY MCP_Server /app/MCP_Server
COPY collaboration /app/collaboration
COPY common /app/common

CMD ["uvicorn", "MCP_Server.cloud_run_gateway:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"
gcloud builds submit "$BUILD_DIR" --tag "$IMAGE_URI"

base_env_vars="CLOUD_TASKS_LOCATION=$REGION,CLOUD_TASKS_QUEUE_REMOTE=$CLOUD_TASKS_QUEUE_REMOTE,CLOUD_TASKS_QUEUE_UNITY=$CLOUD_TASKS_QUEUE_UNITY,CLOUD_TASKS_INTERNAL_TOKEN=$CLOUD_TASKS_INTERNAL_TOKEN"
if [[ -n "$EXTRA_ENV_VARS" ]]; then
  env_vars="${base_env_vars},${EXTRA_ENV_VARS}"
else
  env_vars="$base_env_vars"
fi

deploy_cmd=(
  gcloud run deploy "$SERVICE_NAME"
  --image "$IMAGE_URI"
  --region "$REGION"
  --min-instances 0
  --max-instances 1
  --cpu 1
  --memory 512Mi
  --timeout 300
  --set-env-vars "$env_vars"
)

if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
  deploy_cmd+=(--allow-unauthenticated)
else
  deploy_cmd+=(--no-allow-unauthenticated)
fi

"${deploy_cmd[@]}"

echo "완료: 최소 파일로 Cloud Run 배포 완료"
echo "image: $IMAGE_URI"
