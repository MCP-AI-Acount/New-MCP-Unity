#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
BRANCH_NAME="${BRANCH_NAME:-}"

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  exit 0
fi

resolve_branch() {
  if [[ -n "$BRANCH_NAME" ]]; then
    echo "$BRANCH_NAME"
    return
  fi
  current="$(git branch --show-current 2>/dev/null || true)"
  if [[ -n "$current" ]]; then
    echo "$current"
    return
  fi
  remote_head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
  if [[ -n "$remote_head" ]]; then
    echo "$remote_head"
    return
  fi
  if git show-ref --verify --quiet refs/heads/main; then
    echo "main"
    return
  fi
  if git show-ref --verify --quiet refs/heads/master; then
    echo "master"
    return
  fi
  echo ""
}

target_branch="$(resolve_branch)"
if [[ -z "$target_branch" ]]; then
  exit 0
fi

git fetch origin "$target_branch" || true
git checkout "$target_branch" >/dev/null 2>&1 || true
git pull --rebase origin "$target_branch" || true
