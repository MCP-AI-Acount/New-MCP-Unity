# n8n 연동 (전역 설치 + Cursor MCP)

## 설치

- 전역: `npm install -g n8n` (또는 이미 설치된 `n8n` 명령 사용)
- 실행: 터미널에서 `n8n start` 또는 `EXE/start_n8n.sh`

## Cursor에서 MCP 목록에 안 보일 때

- MCP 본체는 **`~/.cursor/mcp.json`** (macOS) 한 파일로 통일. 여기 `mcpServers`에 `n8n` 블록이 있는지 확인하고, 수정 후 Cursor 재시작.

## 서버 주소

- UI·API 베이스: `http://localhost:5678`
- MCP용 API URL (`~/.cursor/mcp.json` 의 `n8n.env.N8N_API_URL`): `http://localhost:5678/api/v1`

## API 키 (MCP `N8N_API_KEY` 에 넣을 값)

1. n8n 실행 후 브라우저에서 `http://localhost:5678` 접속
2. 최초 실행이면 관리자 계정 생성
3. **Settings(설정)** → **n8n API** (또는 **API**) 메뉴
4. **Create API Key** 로 키 발급 후 복사
5. Cursor MCP 설정에서 `~/.cursor/mcp.json` 의 `n8n` → `N8N_API_KEY` 를 실제 키로 교체 (또는 Cursor 환경변수로 주입)

키는 저장소에 커밋하지 말 것.

## 다른 스크립트와의 환경변수 이름

| 변수 | 용도 |
|------|------|
| `N8N_API_KEY` | MCP 서버 `@leonardsellem/n8n-mcp-server` |
| `N8N_WEBHOOK_URL` | Python 쪽 로그 전송 (`common/n8n_logger.py` 등) — 워크플로에서 Webhook URL 복사 후 사용 |

## 401 이 계속일 때

1. **`n8n start` 대신 `EXE/start_n8n.sh` 사용** — `N8N_PUBLIC_API_DISABLED`·`N8N_AUTH_EXCLUDE_ENDPOINTS` 를 맞춰 둠.
2. **Basic Auth** (`N8N_BASIC_AUTH_ACTIVE=true` 등)를 쓰는 경우, UI 로그인용 Basic 이 **`/api/*` 요청까지 막아** API 키만으로는 401 이 날 수 있음. 위 스크립트는 `N8N_AUTH_EXCLUDE_ENDPOINTS=api` 로 `/api` 는 API 키 검사만 하게 함(공식 커뮤니티 권장).
3. 셸에 **`N8N_PUBLIC_API_DISABLED=true`** 가 남아 있으면 Public API 자체가 꺼짐 → `unset N8N_PUBLIC_API_DISABLED` 후 재실행.
4. 키는 **Settings → API / n8n API** 에서 새로 발급해 `mcp.json` 에 **따옴표 안 한 줄**로만 넣기(앞뒤 공백 없음).
