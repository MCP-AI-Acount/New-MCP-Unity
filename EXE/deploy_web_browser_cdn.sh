#!/usr/bin/env bash
set -euo pipefail

# command: web-browser 정적자산 CDN + Cloud Run 배포
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-web-browser-dashboard}"
BUCKET_NAME="${BUCKET_NAME:-}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-false}"
WEB_STORE_MODE="${WEB_STORE_MODE:-firestore}"
WEB_STORE_COLLECTION="${WEB_STORE_COLLECTION:-web_dashboard_state}"
STATIC_ASSET_BASE_URL="${STATIC_ASSET_BASE_URL:-}"
EXTRA_ENV_VARS="${EXTRA_ENV_VARS:-}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID 환경변수가 필요합니다." >&2
  exit 1
fi

if [[ -z "$BUCKET_NAME" ]]; then
  BUCKET_NAME="${PROJECT_ID}-web-browser-static"
fi

if [[ -z "$STATIC_ASSET_BASE_URL" ]]; then
  STATIC_ASSET_BASE_URL="https://storage.googleapis.com/${BUCKET_NAME}"
fi

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com firestore.googleapis.com >/dev/null

if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET_NAME}"
fi

# 정적 자산 업로드(변경분만 동기화)
gsutil -m rsync -r -d "${REPO_ROOT}/web-browser/static" "gs://${BUCKET_NAME}"

# 정적 자산 캐시/보안 헤더
while IFS= read -r object_path; do
  gsutil setmeta -h "Cache-Control:public, max-age=31536000, immutable" "gs://${BUCKET_NAME}/${object_path}" >/dev/null || true
done < <(cd "${REPO_ROOT}/web-browser/static" && rg --files)

base_env_vars="STATIC_ASSET_BASE_URL=${STATIC_ASSET_BASE_URL},WEB_STORE_MODE=${WEB_STORE_MODE},WEB_STORE_COLLECTION=${WEB_STORE_COLLECTION},CURSOR_RULES_FILE=/app/data/cursor_top_rules.md"
if [[ -n "$EXTRA_ENV_VARS" ]]; then
  env_vars="${base_env_vars},${EXTRA_ENV_VARS}"
else
  env_vars="$base_env_vars"
fi

deploy_cmd=(
  gcloud run deploy "$SERVICE_NAME"
  --source "${REPO_ROOT}"
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

echo "완료: web-browser CDN 분리 배포 완료"
echo "static bucket: gs://${BUCKET_NAME}"
echo "static url: ${STATIC_ASSET_BASE_URL}"
