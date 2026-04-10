# Remote Unity Stack Runbook (맥 OFF 기준)

## 구조

- Cursor Cloud Agent: 코드 변경, MCP 호출
- Cloud Run (`MCP_Server/cloud_run_gateway.py`): HTTPS 제어 허브
- GCP VM (`MCP_Server/unity_worker_gateway.py`): Headless Unity 실행 워커
- n8n: 결과 로그 수집/시트 기록

## 1. 기본 인프라 생성

```bash
chmod +x EXE/setup_remote_unity_stack.sh
PROJECT_ID=<your-project-id> REGION=asia-northeast3 ZONE=asia-northeast3-a EXE/setup_remote_unity_stack.sh
```

Cloud Run 최소 배포(게이트웨이만)만 따로 수행하려면:

```bash
bash EXE/deploy_cloud_run_gateway_minimal.sh
```

- 이 스크립트는 임시 빌드 디렉토리를 만들고
- `MCP_Server/`, `collaboration/`, `common/`, `requirements-cloudrun.txt`만 포함해
- Cloud Run에 최소 소스만 배포합니다.
- Unity 프로젝트(씬/에셋)는 Git 저장소/VM 경로에 유지하며 Cloud Run에는 올리지 않습니다.

## 2. VM에 Unity Worker 올리기

1) VM 접속 후 Python 설치
2) 저장소 클론
3) 의존성 설치

```bash
pip3 install fastapi "uvicorn[standard]"
```

4) 환경변수 설정

```bash
export UNITY_WORKER_BEARER_TOKEN="<worker-token>"
export UNITY_PROJECT_PATH="/home/<user>/unity/YourProject"
export UNITY_PATH="/opt/unity/Editor/Unity"
export UNITY_BATCH_METHOD="RemoteAutomation.EntryPoint"
```

5) 워커 실행

```bash
uvicorn MCP_Server.unity_worker_gateway:app --host 0.0.0.0 --port 8443
```

## 3. Cloud Run에서 Unity 작업 호출

```bash
curl -X POST "https://<cloud-run-url>/v1/unity/tasks/run" \
  -H "Authorization: Bearer <REMOTE_API_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"unity-req-1",
    "task_type":"ui_add_login_panel",
    "task_payload":{
      "scene":"SampleScene",
      "parent":"Canvas",
      "objects":["Panel","InputEmail","InputPassword","LoginButton"]
    },
    "unity_worker_url":"https://<vm-public-ip>:8443",
    "n8n_webhook_url":"https://<n8n-webhook>"
  }'
```

비동기(기본값, 휴대폰 대기모드 대비):

```bash
curl -X POST "https://<cloud-run-url>/v1/unity/tasks/run" \
  -H "Authorization: Bearer <REMOTE_API_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"unity-req-2",
    "task_type":"set_canvas_graph_horizontal_green",
    "task_payload":{
      "scene":"SampleScene",
      "canvasName":"Canvas",
      "graphName":"Graph",
      "colorHex":"#00FF00"
    },
    "project_name":"ReportMaker",
    "unity_worker_url":"https://<vm-public-ip>:8443",
    "n8n_webhook_url":"https://<n8n-webhook>",
    "run_async": true
  }'
```

응답에는 `accepted=true` 와 `cloud_task_name` 이 반환되며, 작업 결과는 `n8n_webhook_url`로 수신합니다.  
Cloud Tasks 큐에 들어간 작업은 클라이언트(아이폰) 연결이 끊겨도 백그라운드에서 계속 진행됩니다.

## 4. 무료티어/비용 전략

- Cloud Run: `min-instances=0`, `max-instances=1`
- VM: 평시 중지, 작업 시간에만 시작(스케줄러 사용)
- 로그/스토리지 수명주기 정책 적용

## 5. 보안

- Bearer 토큰은 Secret Manager 사용
- VM 포트는 IP 제한 권장(0.0.0.0/0 사용 지양)
- HTTPS 인증서는 반드시 적용(Load Balancer 또는 Tailscale/WireGuard 권장)
