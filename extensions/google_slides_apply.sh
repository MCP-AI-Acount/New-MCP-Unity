#!/usr/bin/env bash
set -euo pipefail

IN_FILE="${1:-}"
if [[ -z "$IN_FILE" ]]; then
  echo "usage: $0 <comic.json>" >&2
  exit 1
fi

if [[ ! -f "$IN_FILE" ]]; then
  echo "[google_slides_apply] missing input: $IN_FILE" >&2
  exit 1
fi

# Placeholder to keep pipeline cloud-runnable without local mac dependency.
# Replace with Google Slides API apply logic in connected environment.
echo "[google_slides_apply] would apply content to presentation: ${GOOGLE_PRESENTATION_ID:-unset}"
echo "[google_slides_apply] input: $IN_FILE"
