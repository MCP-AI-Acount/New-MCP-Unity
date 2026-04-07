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

## Cursor 제한 관련

Cursor 원본 대화 DB를 공식 API로 그대로 미러링하는 것은 제한될 수 있어, 이 앱은 별도 메시지 로그(`data/messages.json`)를 기준으로 동작.
