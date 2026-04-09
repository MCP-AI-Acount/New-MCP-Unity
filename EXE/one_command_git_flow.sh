#!/usr/bin/env bash
set -euo pipefail

# command: git 변경사항 add/commit/push 한 번에 실행
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMMIT_MSG="${1:-}"

if [[ -z "$COMMIT_MSG" ]]; then
  echo "usage: bash \"$REPO_ROOT/EXE/one_command_git_flow.sh\" \"<commit message>\"" >&2
  exit 1
fi

cd "$REPO_ROOT"

if [[ ! -d .git ]]; then
  echo "[one_command] git 저장소가 아닙니다: $REPO_ROOT" >&2
  exit 1
fi

# VM에서 권한 관련 경고를 줄이기 위해 현재 저장소를 safe.directory에 등록.
git config --global --add safe.directory "$REPO_ROOT" >/dev/null 2>&1 || true

current_branch="$(git branch --show-current)"
if [[ -z "$current_branch" ]]; then
  if git show-ref --verify --quiet refs/heads/main; then
    git checkout main >/dev/null
  elif git show-ref --verify --quiet refs/heads/master; then
    git checkout master >/dev/null
  else
    auto_branch="auto/$(date +%Y%m%d-%H%M%S)"
    git checkout -b "$auto_branch" >/dev/null
  fi
  current_branch="$(git branch --show-current)"
fi

if [[ -z "$(git status --porcelain)" ]]; then
  echo "[one_command] 변경사항 없음"
  exit 0
fi

git add -A
mapfile -t staged_files < <(git diff --cached --name-only)
if [[ "${#staged_files[@]}" -eq 0 ]]; then
  echo "[one_command] 스테이징된 변경사항 없음"
  exit 0
fi

# 간단한 시크릿 패턴 차단 (실수 커밋 방지)
if rg -n --no-messages "(AIza[0-9A-Za-z_-]{20,}|ntn_[0-9A-Za-z]+|EA[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)" "${staged_files[@]}" >/dev/null 2>&1; then
  echo "[one_command] secret pattern detected in staged files. commit 중단." >&2
  exit 1
fi

git commit -m "$COMMIT_MSG"

load_pat() {
  local candidates=()
  if [[ -n "${ENV_FILE_PATH:-}" ]]; then
    candidates+=("${ENV_FILE_PATH}")
  fi
  candidates+=(
    "$HOME/.config/agent-secrets.env"
    "/home/ubuntu/.config/agent-secrets.env"
    "/home/GCP/ReportMaker/temp/agent-secrets.env"
    "$REPO_ROOT/temp/agent-secrets.env"
  )

  local env_file
  for env_file in "${candidates[@]}"; do
    if [[ -f "$env_file" ]]; then
      # shellcheck disable=SC1090
      source "$env_file"
      if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        export GITHUB_TOKEN
        return 0
      fi
    fi
  done
  return 1
}

to_github_https_url() {
  local remote_url="$1"
  if [[ "$remote_url" =~ ^git@github\.com:(.+)\.git$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}.git"
    return 0
  fi
  if [[ "$remote_url" =~ ^https://github\.com/.+\.git$ ]]; then
    echo "$remote_url"
    return 0
  fi
  if [[ "$remote_url" =~ ^https://github\.com/.+$ ]]; then
    echo "${remote_url}.git"
    return 0
  fi
  return 1
}

is_network_error() {
  local output="$1"
  if printf "%s" "$output" | rg -q -i "Could not resolve host|Connection timed out|Operation timed out|Network is unreachable|Connection reset|TLS handshake timeout|Temporary failure in name resolution"; then
    return 0
  fi
  return 1
}

push_with_retry() {
  local mode="$1"
  local attempt=1
  local delay=4
  local output=""

  while [[ "$attempt" -le 5 ]]; do
    if [[ "$mode" == "token" ]]; then
      output="$(
        GIT_TERMINAL_PROMPT=0 git \
          -c "http.https://github.com/.extraheader=AUTHORIZATION: basic ${GITHUB_BASIC_AUTH}" \
          push "${PUSH_TARGET_URL}" "${current_branch}:${current_branch}" 2>&1
      )" && {
        printf "%s\n" "$output"
        return 0
      }
    else
      output="$(GIT_TERMINAL_PROMPT=0 git push -u origin "$current_branch" 2>&1)" && {
        printf "%s\n" "$output"
        return 0
      }
    fi

    printf "%s\n" "$output" >&2
    if ! is_network_error "$output"; then
      return 1
    fi

    if [[ "$attempt" -ge 5 ]]; then
      return 1
    fi

    sleep "$delay"
    delay=$((delay * 2))
    attempt=$((attempt + 1))
  done

  return 1
}

origin_url="$(git remote get-url origin 2>/dev/null || true)"
if [[ -z "$origin_url" ]]; then
  echo "[one_command] origin remote 없음. push 생략." >&2
  exit 1
fi

if load_pat; then
  token_loaded="1"
else
  token_loaded="0"
  echo "[one_command] GITHUB_TOKEN 없음 — 일반 git 자격증명으로 push 시도." >&2
fi

PUSH_TARGET_URL=""
if [[ "$token_loaded" == "1" ]]; then
  if github_https_url="$(to_github_https_url "$origin_url")"; then
    PUSH_TARGET_URL="$github_https_url"
    GITHUB_BASIC_AUTH="$(printf "x-access-token:%s" "$GITHUB_TOKEN" | base64 | tr -d '\n')"
    if push_with_retry "token"; then
      git fetch origin "$current_branch" >/dev/null 2>&1 || true
      git branch --set-upstream-to="origin/$current_branch" "$current_branch" >/dev/null 2>&1 || true
      echo "[one_command] 완료: commit + push"
      exit 0
    fi
    echo "[one_command] 토큰 기반 push 실패. 일반 push 재시도." >&2
  fi
fi

if push_with_retry "origin"; then
  echo "[one_command] 완료: commit + push"
  exit 0
fi

echo "[one_command] push 실패. 인증 설정 또는 네트워크를 확인하세요." >&2
exit 1
