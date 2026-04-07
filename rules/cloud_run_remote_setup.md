# Cloud Run 원격 MCP 실행 절차

## 1) API 활성화

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

## 2) 배포

```bash
gcloud config set project <GCP_PROJECT_ID>
gcloud run deploy remote-mcp-gateway \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars REMOTE_API_BEARER_TOKEN=<YOUR_TOKEN>,N8N_WEBHOOK_URL=<YOUR_WEBHOOK> \
  --min-instances 0 \
  --max-instances 1 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 300
```

## 3) 모바일 테스트

```bash
curl -X GET "https://<cloud-run-url>/healthz"
```

```bash
curl -X POST "https://<cloud-run-url>/v1/tasks/run" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"mobile-test-1",
    "task_type":"screenshot_to_sheet",
    "image_path":"temp/capture.png",
    "template_path":"rules/sheets_ocr_template.example.json",
    "spreadsheet_id":"<SPREADSHEET_ID>",
    "dry_run": true
  }'
```

## 4) 무료 티어 고려

- `--min-instances 0` 유지
- `--max-instances 1`로 급격한 과금 방지
- 장시간 작업이 아니면 `CPU always allocated` 옵션 비활성 유지
- Artifact Registry 이미지 정리 주기 설정

## 5) 데이터 학습 제외/보안

- Gemini API 사용 시 프로젝트 정책에서 데이터 로깅/학습 옵션 확인
- 민감 데이터는 n8n 전송 전 마스킹
- API 키는 Secret Manager 사용
