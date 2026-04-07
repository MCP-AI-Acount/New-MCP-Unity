#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
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
