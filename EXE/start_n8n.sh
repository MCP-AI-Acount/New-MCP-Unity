#!/usr/bin/env bash
# 명령: 전역 n8n 서버 기동 (기본 http://localhost:5678) — MCP N8N_API_URL 과 맞춤

set -euo pipefail
if ! command -v n8n >/dev/null 2>&1; then
  echo "n8n 명령을 찾을 수 없습니다. npm install -g n8n 후 PATH를 확인하세요."
  exit 1
fi
# Public REST API 가 꺼져 있으면 API 키로도 401 — 미설정 시 명시적으로 허용
export N8N_PUBLIC_API_DISABLED="${N8N_PUBLIC_API_DISABLED:-false}"
# Basic Auth(N8N_BASIC_AUTH_*) 사용 시 /api 가 먼저 막혀 API 키만으로 401 날 수 있음 — /api 는 API 키로만 검사
export N8N_AUTH_EXCLUDE_ENDPOINTS="${N8N_AUTH_EXCLUDE_ENDPOINTS:-api}"
exec n8n start
