#!/usr/bin/env bash
set -euo pipefail

# 명령: 네이버 대표 뉴스 1건을 만화 요약으로 만들어 구글 프레젠테이션에 반영

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/common/load_secrets.sh"

if [[ ! -x "$ROOT_DIR/extensions/naver_news_to_story.sh" ]]; then
  echo "[run] missing executable: $ROOT_DIR/extensions/naver_news_to_story.sh" >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/extensions/gemini_story_to_comic.sh" ]]; then
  echo "[run] missing executable: $ROOT_DIR/extensions/gemini_story_to_comic.sh" >&2
  exit 1
fi

if [[ ! -x "$ROOT_DIR/extensions/google_slides_apply.sh" ]]; then
  echo "[run] missing executable: $ROOT_DIR/extensions/google_slides_apply.sh" >&2
  exit 1
fi

WORK_DIR="$ROOT_DIR/temp/news_to_comic"
mkdir -p "$WORK_DIR"

"$ROOT_DIR/extensions/naver_news_to_story.sh" "$WORK_DIR/story.json"
"$ROOT_DIR/extensions/gemini_story_to_comic.sh" "$WORK_DIR/story.json" "$WORK_DIR/comic.json"
"$ROOT_DIR/extensions/google_slides_apply.sh" "$WORK_DIR/comic.json"

echo "[run] completed news -> comic -> slides pipeline"
