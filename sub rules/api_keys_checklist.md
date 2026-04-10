# API 키/시크릿 체크리스트

## Cloud Run 배포/운영

- `GCP_PROJECT_ID`
- `GCP_REGION` (예: `asia-northeast3`)
- `REMOTE_API_BEARER_TOKEN` (Cloud Run HTTPS API 보호용)
- `UNITY_WORKER_URL` (Cloud Run -> VM 워커 호출 주소)
- `UNITY_WORKER_BEARER_TOKEN` (VM 워커 API 보호용)

## Google Sheets/Calendar

- `MCP_Server/credentials.json` (OAuth Client)
- `MCP_Server/token_sheets.json` (초기 인증 후 생성)
- `MCP_Server/token.json` (캘린더 OAuth 사용 시)
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_API_KEY` (캘린더 API 키 모드 사용 시)

## n8n

- 전역 설치·MCP 연동: `sub rules/api_keys_n8n.md`
- `N8N_WEBHOOK_URL` (Python 웹훅 로그)
- MCP: `N8N_API_KEY` + `N8N_API_URL` (`http://localhost:5678/api/v1`)

## Unity 로그인

- `FIREBASE_WEB_API_KEY` (Firebase Auth REST 사용 시)
- 커스텀 로그인 API 사용 시 백엔드 API URL/토큰
- Unity License 관련 파일/환경변수 (Headless 실행 시 필수)

## 보안 메모

- 실제 키/토큰은 소스코드에 하드코딩하지 말고 환경변수 또는 Secret Manager 사용
- 이미 노출된 키는 즉시 재발급/폐기
