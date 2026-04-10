#!/usr/bin/env bash
set -euo pipefail

# command: # you/keys.env 를 읽어 환경변수로 로드
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
YOU_KEYS_FILE="${YOU_KEYS_FILE:-$REPO_ROOT/# you/keys.env}"

if [[ ! -f "$YOU_KEYS_FILE" ]]; then
  exit 0
fi

set -a
# shellcheck disable=SC1090
source "$YOU_KEYS_FILE"
set +a
