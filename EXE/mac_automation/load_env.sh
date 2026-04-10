#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-$REPO_DIR/rules/.env.local}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "env file not found: $ENV_FILE"
  echo "cp \"$REPO_DIR/rules/.env.example\" \"$REPO_DIR/rules/.env.local\" 후 값 입력"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

echo "loaded env from $ENV_FILE"
