#!/usr/bin/env bash
set -euo pipefail

# Load runtime secrets from secure local path outside git repo.
# Priority:
# 1) ENV_FILE_PATH explicit path
# 2) /home/ubuntu/.config/agent-secrets.env
# 3) /workspace/temp/agent-secrets.env (fallback for ephemeral testing)

ENV_FILE_PATH="${ENV_FILE_PATH:-}"
DEFAULT_SECURE_ENV="/home/ubuntu/.config/agent-secrets.env"
FALLBACK_ENV="/workspace/temp/agent-secrets.env"
_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_REPO_ENV="${_REPO_ROOT}/temp/agent-secrets.env"

if [[ -n "$ENV_FILE_PATH" && -f "$ENV_FILE_PATH" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE_PATH"
elif [[ -f "$DEFAULT_SECURE_ENV" ]]; then
  # shellcheck disable=SC1091
  source "$DEFAULT_SECURE_ENV"
elif [[ -f "$FALLBACK_ENV" ]]; then
  # shellcheck disable=SC1091
  source "$FALLBACK_ENV"
elif [[ -f "$LOCAL_REPO_ENV" ]]; then
  # shellcheck disable=SC1091
  source "$LOCAL_REPO_ENV"
else
  echo "[load_secrets] secret env file not found" >&2
  echo "[load_secrets] expected one of:" >&2
  echo "  - ENV_FILE_PATH" >&2
  echo "  - $DEFAULT_SECURE_ENV" >&2
  echo "  - $FALLBACK_ENV" >&2
  echo "  - $LOCAL_REPO_ENV" >&2
  exit 1
fi

required_vars=(
  GEMINI_API_KEY
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN
  GOOGLE_PRESENTATION_ID
)

missing=0
for key in "${required_vars[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "[load_secrets] missing required var: $key" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

export GEMINI_API_KEY
export GOOGLE_CLIENT_ID
export GOOGLE_CLIENT_SECRET
export GOOGLE_REFRESH_TOKEN
export GOOGLE_PRESENTATION_ID

echo "[load_secrets] secrets loaded successfully"
