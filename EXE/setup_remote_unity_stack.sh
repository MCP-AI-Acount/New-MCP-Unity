#!/usr/bin/env bash
# 명령: Cloud Run + GCP VM(Unity Worker) 원격 자동화 스택 초기 세팅

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-remote-mcp-gateway}"
REPO_NAME="${REPO_NAME:-remote-mcp-repo}"
VM_NAME="${VM_NAME:-unity-headless-worker}"
ZONE="${ZONE:-asia-northeast3-a}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-4}"
CLOUD_TASKS_QUEUE_REMOTE="${CLOUD_TASKS_QUEUE_REMOTE:-remote-mcp-tasks}"
CLOUD_TASKS_QUEUE_UNITY="${CLOUD_TASKS_QUEUE_UNITY:-remote-mcp-unity-tasks}"
CLOUD_TASKS_INTERNAL_TOKEN="${CLOUD_TASKS_INTERNAL_TOKEN:-}"
EXTRA_ENV_VARS="${EXTRA_ENV_VARS:-}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-false}"
UNITY_WORKER_SOURCE_RANGES="${UNITY_WORKER_SOURCE_RANGES:-}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID 환경변수가 필요합니다."
  exit 1
fi

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com compute.googleapis.com cloudtasks.googleapis.com

if ! gcloud artifacts repositories describe "$REPO_NAME" --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format docker \
    --location "$REGION"
fi

if ! gcloud tasks queues describe "$CLOUD_TASKS_QUEUE_REMOTE" --location "$REGION" >/dev/null 2>&1; then
  gcloud tasks queues create "$CLOUD_TASKS_QUEUE_REMOTE" \
    --location "$REGION"
fi

if ! gcloud tasks queues describe "$CLOUD_TASKS_QUEUE_UNITY" --location "$REGION" >/dev/null 2>&1; then
  gcloud tasks queues create "$CLOUD_TASKS_QUEUE_UNITY" \
    --location "$REGION"
fi

if [[ -z "$CLOUD_TASKS_INTERNAL_TOKEN" ]]; then
  CLOUD_TASKS_INTERNAL_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
fi

PROJECT_ID="$PROJECT_ID" \
REGION="$REGION" \
SERVICE_NAME="$SERVICE_NAME" \
REPO_NAME="$REPO_NAME" \
CLOUD_TASKS_QUEUE_REMOTE="$CLOUD_TASKS_QUEUE_REMOTE" \
CLOUD_TASKS_QUEUE_UNITY="$CLOUD_TASKS_QUEUE_UNITY" \
CLOUD_TASKS_INTERNAL_TOKEN="$CLOUD_TASKS_INTERNAL_TOKEN" \
EXTRA_ENV_VARS="$EXTRA_ENV_VARS" \
ALLOW_UNAUTHENTICATED="$ALLOW_UNAUTHENTICATED" \
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy_cloud_run_gateway_minimal.sh"

if ! gcloud compute instances describe "$VM_NAME" --zone "$ZONE" >/dev/null 2>&1; then
  gcloud compute instances create "$VM_NAME" \
    --zone "$ZONE" \
    --machine-type "$MACHINE_TYPE" \
    --image-family ubuntu-2204-lts \
    --image-project ubuntu-os-cloud \
    --boot-disk-size 100GB \
    --tags unity-worker
fi

if [[ -z "$UNITY_WORKER_SOURCE_RANGES" ]]; then
  echo "UNITY_WORKER_SOURCE_RANGES 환경변수가 필요합니다. 예: 203.0.113.0/24"
  echo "보안상 0.0.0.0/0 기본 허용은 비활성화했습니다."
  exit 1
fi

if ! gcloud compute firewall-rules describe allow-unity-worker-8443 >/dev/null 2>&1; then
  gcloud compute firewall-rules create allow-unity-worker-8443 \
    --allow tcp:8443 \
    --target-tags unity-worker \
    --source-ranges "$UNITY_WORKER_SOURCE_RANGES"
fi

echo "완료: Cloud Run 및 VM 기본 리소스 생성 완료"
