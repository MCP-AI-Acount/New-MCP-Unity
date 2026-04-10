# Cloud Bridge Agent 설정

목표:
- 아이폰/맥/클라우드에서 동일 세션 공유
- 클라우드가 큐에 넣은 명령을 맥이 자동 실행
- 실행 결과를 다시 클라우드로 전송

## 1) 환경변수 준비

`main rules/.env.local` 또는 맥 셸 환경에 아래 값 설정:

```bash
CLOUD_RUN_URL=https://<your-cloud-run-url>
REMOTE_API_BEARER_TOKEN=<your-remote-api-token>
BRIDGE_DEVICE_ID=mac-main
BRIDGE_POLL_SECONDS=3
```

## 2) 설치

맥에서 저장소 루트 기준:

```bash
BRIDGE_BASE_URL="$CLOUD_RUN_URL" BRIDGE_AUTH_TOKEN="$REMOTE_API_BEARER_TOKEN" DEVICE_ID="mac-main" bash EXE/mac_automation/install_bridge_agent.sh
```

## 3) 동작

- 에이전트는 `com.newmcp.bridge.agent` launch agent로 실행됨
- 주기적으로 `/v1/bridge/commands/claim` 호출
- 받은 명령을 `/bin/bash -lc "<command>"`로 실행
- stdout/stderr/exit_code를 `/v1/bridge/commands/result`로 업로드

## 4) 운영 메모

- 클라우드에 명령 넣기: `/v1/bridge/commands`
- 맥 실행 결과 확인: `/v1/bridge/commands/list`
- 채팅/상태 공유: `/v1/bridge/messages/*`
