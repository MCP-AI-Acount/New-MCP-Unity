#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
BRANCH_NAME="${BRANCH_NAME:-master}"
IDLE_THRESHOLD_SECONDS="${IDLE_THRESHOLD_SECONDS:-300}"
COMMIT_MESSAGE_PREFIX="${COMMIT_MESSAGE_PREFIX:-auto: idle checkpoint}"
AUTO_PUSH="${AUTO_PUSH:-0}"
ALLOW_PATHS_REGEX="${ALLOW_PATHS_REGEX:-^(MCP_Server/|collaboration/|common/|extensions/|rules/|EXE/|2_Option/|Option/|\\.gitignore$)}"

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  exit 0
fi

if [[ -n "$(git status --porcelain)" ]]; then
  idle_hex="$(ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF; exit}')"
  idle_ns=$((idle_hex))
  idle_sec=$((idle_ns / 1000000000))
  if (( idle_sec < IDLE_THRESHOLD_SECONDS )); then
    exit 0
  fi

  mapfile -t changed_files < <(git status --porcelain | awk '{print $2}')
  for f in "${changed_files[@]}"; do
    if [[ "$f" =~ $ALLOW_PATHS_REGEX ]]; then
      git add -- "$f"
    fi
  done

  if [[ -n "$(git diff --cached --name-only)" ]]; then
    if rg -n "(AIza[0-9A-Za-z_-]{20,}|ntn_[0-9A-Za-z]+|EA[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)" "$(git diff --cached --name-only)" >/dev/null 2>&1; then
      echo "secret pattern detected in staged files. auto commit skipped."
      exit 0
    fi
    git commit -m "${COMMIT_MESSAGE_PREFIX} $(date '+%Y-%m-%d %H:%M:%S')"
    if [[ "$AUTO_PUSH" == "1" ]]; then
      git push origin "$BRANCH_NAME" || true
    fi
  fi
fi
