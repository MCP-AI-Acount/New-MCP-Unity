#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SOURCE_GITIGNORE="$REPO_DIR/.gitignore"
TARGET_DIR="${1:-}"

if [[ -z "$TARGET_DIR" ]]; then
  echo "usage: $0 <new-project-dir>"
  exit 1
fi

mkdir -p "$TARGET_DIR"

if [[ ! -f "$TARGET_DIR/.gitignore" ]]; then
  cp "$SOURCE_GITIGNORE" "$TARGET_DIR/.gitignore"
  exit 0
fi

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  if ! rg -n "^${line//\//\\/}$" "$TARGET_DIR/.gitignore" >/dev/null 2>&1; then
    echo "$line" >> "$TARGET_DIR/.gitignore"
  fi
done < "$SOURCE_GITIGNORE"
