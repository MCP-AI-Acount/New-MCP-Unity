#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
cd "$REPO_DIR"

echo "[check] gitignore exists"
[[ -f ".gitignore" ]] || { echo "missing .gitignore"; exit 1; }

echo "[check] sensitive patterns in tracked files"
if rg -n "(AIza[0-9A-Za-z_-]{20,}|ntn_[0-9A-Za-z]+|EA[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)" 1_Main MCP_Server EXE common collaboration rules extensions >/tmp/newmcp-secret-scan.txt 2>/dev/null; then
  echo "warning: sensitive-like strings found"
  if [[ -s /tmp/newmcp-secret-scan.txt ]]; then
    awk 'NR<=30 {print} NR==31 {print "... (truncated)"}' /tmp/newmcp-secret-scan.txt
  fi
else
  echo "ok: no obvious sensitive patterns"
fi

echo "[check] recommended env vars"
for k in REMOTE_API_BEARER_TOKEN UNITY_WORKER_BEARER_TOKEN N8N_WEBHOOK_URL; do
  if [[ -z "${!k:-}" ]]; then
    echo "missing env: $k"
  else
    echo "ok env: $k"
  fi
done
