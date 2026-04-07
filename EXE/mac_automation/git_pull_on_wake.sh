#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
BRANCH_NAME="${BRANCH_NAME:-master}"

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  exit 0
fi

git fetch origin "$BRANCH_NAME" || true
git pull --rebase origin "$BRANCH_NAME" || true
