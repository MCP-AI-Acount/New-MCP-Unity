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
  --no-allow-unauthenticated \
  --set-env-vars REMOTE_API_BEARER_TOKEN=<YOUR_TOKEN>,N8N_WEBHOOK_URL=<YOUR_WEBHOOK> \
  --min-instances 0 \
  --max-instances 1 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 300
```

### REMOTE_API_BEARER_TOKEN 을 «어디서 찾나»

- **미리 GCP에 저장돼 있는 값이 아닙니다.** 배포할 때 **직접 정한 비밀 문자열**이고, 그걸 서비스 환경 변수 `REMOTE_API_BEARER_TOKEN` 에 넣어 둔 것입니다.
- **배포 명령**에서 `--set-env-vars REMOTE_API_BEARER_TOKEN=<YOUR_TOKEN>` 으로 넣었다면, 그때 `<YOUR_TOKEN>` 자리에 썼던 문자열이 곧 토큰입니다. (로컬 메모·배포 스크립트·CI 시크릿에 있을 수 있음.)

**Cloud Run 콘솔에서 확인**

1. [Google Cloud Console](https://console.cloud.google.com/) → **Cloud Run**
2. 해당 **리전**(예: `asia-northeast3`) 선택 후 **서비스 이름** 클릭 (예: `remote-mcp-gateway`)
3. 상단 **「편집 및 새 리비전 배포」** 또는 **「수정」** 으로 들어가 **「변수 및 보안」** / **「Variables & Secrets」** 탭
4. **환경 변수** 목록에서 **`REMOTE_API_BEARER_TOKEN`** 행의 **값**이 서버가 기대하는 비밀값입니다. (화면에 마스킹이면, 값을 본인이 새로 저장해 둔 곳만 신뢰 가능.)

**gcloud CLI로 확인**

```bash
gcloud run services describe remote-mcp-gateway \
  --region asia-northeast3 \
  --format='yaml(spec.template.spec.containers[0].env)'
```

출력 YAML 안에 `name: REMOTE_API_BEARER_TOKEN` 의 `value` 가 보입니다. (보안상 값이 숨겨지는 경우도 있어, **원래 정한 문자열은 로컬에 따로 보관**하는 것이 안전합니다.)

**MCP `headers.Authorization` 에 넣는 형식**

- `Bearer ` + (위와 **동일한** 문자열)  
- 예: 토큰이 `my-secret-abc` 이면 → `Authorization: Bearer my-secret-abc`

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
    "template_path":"main rules/sheets_ocr_template.example.json",
    "spreadsheet_id":"<SPREADSHEET_ID>",
    "dry_run": true
  }'
```

## 4) 무료 티어 고려

- `--min-instances 0` 유지
- `--max-instances 1`로 급격한 과금 방지
- 장시간 작업이 아니면 `CPU always allocated` 옵션 비활성 유지
- Artifact Registry 이미지 정리 주기 설정

## 4-1) 권장 배포 스크립트 (보안/최소배포)

저장소 루트에서:

```bash
ALLOW_UNAUTHENTICATED=false \
UNITY_WORKER_SOURCE_RANGES=<허용CIDR> \
bash EXE/setup_remote_unity_stack.sh
```

- `ALLOW_UNAUTHENTICATED=false` 기본 (인증 없는 공개 엔드포인트 방지)
- `UNITY_WORKER_SOURCE_RANGES` 필수 (예: `203.0.113.0/24`)  
  `0.0.0.0/0` 공개 허용은 권장하지 않음

## 5) 데이터 학습 제외/보안

- Gemini API 사용 시 프로젝트 정책에서 데이터 로깅/학습 옵션 확인
- 민감 데이터는 n8n 전송 전 마스킹
- API 키는 Secret Manager 사용
