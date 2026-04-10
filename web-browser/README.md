# web-browser

아이폰에서 보는 원격 개발 대시보드 웹앱.

## 로컬 실행

```bash
cd "/Users/Windows/Documents/MCP_ Sort/NewMCP/web-browser"
python3 -m pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8090
```

접속:
- `http://127.0.0.1:8090`
- `http://<맥의IP>:8090`

## Cloud Run 배포

```bash
cd "/Users/Windows/Documents/MCP_ Sort/NewMCP"
gcloud run deploy web-browser-dashboard \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars CLOUD_RUN_HEALTH_URL=https://<your-cloud-run-healthz>,UNITY_WORKER_HEALTH_URL=https://<your-worker-healthz>,N8N_STATUS_URL=https://<your-n8n-status-url>
```

배포 후 URL을 아이폰 Safari에서 열면 사용 가능.

## 권장 배포(정적 자산 CDN 분리 + Firestore 상태 저장)

```bash
PROJECT_ID=<your-project-id> \
REGION=asia-northeast3 \
SERVICE_NAME=web-browser-dashboard \
BUCKET_NAME=<your-static-bucket> \
ALLOW_UNAUTHENTICATED=false \
WEB_STORE_MODE=firestore \
bash EXE/deploy_web_browser_cdn.sh
```

동작:
- `web-browser/static` 변경분만 GCS 버킷으로 동기화
- Cloud Run은 API/동적 HTML만 담당
- `STATIC_ASSET_BASE_URL`로 CDN 자산 URL 사용
- `WEB_STORE_MODE=firestore`로 Cloud Run 재시작/스케일에도 상태 일관성 유지

## Cursor 제한 관련

Cursor 원본 대화 DB를 공식 API로 그대로 미러링하는 것은 제한될 수 있어, 이 앱은 별도 메시지 로그(`data/messages.json`)를 기준으로 동작.
