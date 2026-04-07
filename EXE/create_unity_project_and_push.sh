#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:-}"
BASE_DIR="${BASE_DIR:-/Users/Windows/Documents/Task}"
GITHUB_USERNAME="${GITHUB_USERNAME:-MCP-AI-Acount}"
UNITY_PATH="${UNITY_PATH:-/Applications/Unity/Hub/Editor/6000.4.1f1/Unity.app/Contents/MacOS/Unity}"
PROJECT_PATH="$BASE_DIR/$PROJECT_NAME"

if [[ -z "$PROJECT_NAME" ]]; then
  echo "usage: $0 <project-name>"
  exit 1
fi

mkdir -p "$BASE_DIR"

if [[ ! -x "$UNITY_PATH" ]]; then
  echo "Unity 실행 파일 없음: $UNITY_PATH"
  exit 1
fi

if [[ -d "$PROJECT_PATH/.git" ]]; then
  echo "이미 git 저장소가 존재합니다: $PROJECT_PATH"
  exit 1
fi

"$UNITY_PATH" -batchmode -nographics -quit -createProject "$PROJECT_PATH" -logFile "/tmp/unity-create-$PROJECT_NAME.log"

cd "$PROJECT_PATH"
if [[ ! -f ".gitignore" ]]; then
  cp "/Users/Windows/Documents/MCP_ Sort/NewMCP/.gitignore" ".gitignore"
fi

git init
git add -A
git commit -m "chore: initialize Unity project $PROJECT_NAME"

if gh repo view "$GITHUB_USERNAME/$PROJECT_NAME" >/dev/null 2>&1; then
  echo "GitHub repo already exists: $GITHUB_USERNAME/$PROJECT_NAME"
else
  gh repo create "$GITHUB_USERNAME/$PROJECT_NAME" --private --source . --remote origin --push
  exit 0
fi

if ! git remote | rg -n "^origin$" >/dev/null 2>&1; then
  git remote add origin "https://github.com/$GITHUB_USERNAME/$PROJECT_NAME.git"
fi

git branch -M main
git push -u origin main
