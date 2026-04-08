#!/usr/bin/env bash
set -euo pipefail

OUT_FILE="${1:-}"
if [[ -z "$OUT_FILE" ]]; then
  echo "usage: $0 <out_file.json>" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_FILE")"

# Placeholder generic output so pipeline can run in cloud.
# Replace internals with MCP/Web fetch logic when credentials are connected.
cat > "$OUT_FILE" <<JSON
{
  "source": "naver",
  "headline": "placeholder headline",
  "summary": "placeholder summary",
  "panels": [
    "panel 1: setup",
    "panel 2: development",
    "panel 3: result"
  ]
}
JSON

echo "[naver_news_to_story] wrote $OUT_FILE"
