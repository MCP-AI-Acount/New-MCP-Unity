#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

SOURCE_RULE_FILE="${SOURCE_RULE_FILE:-$REPO_DIR/.cursor/rules/cursor_top_rules.md}"
if [[ ! -f "$SOURCE_RULE_FILE" ]]; then
  SOURCE_RULE_FILE="$REPO_DIR/web-browser/data/cursor_top_rules.md"
fi

if [[ ! -f "$SOURCE_RULE_FILE" ]]; then
  echo "[sync_cursor_rules] source rule file not found" >&2
  exit 1
fi

TARGET_RULE_FILE="${TARGET_RULE_FILE:-$HOME/.cursor/rules/cursor_top_rules.md}"

mkdir -p "$(dirname "$TARGET_RULE_FILE")"
cp "$SOURCE_RULE_FILE" "$TARGET_RULE_FILE"

echo "[sync_cursor_rules] synced: $SOURCE_RULE_FILE -> $TARGET_RULE_FILE"
