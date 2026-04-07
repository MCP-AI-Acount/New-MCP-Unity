# 아이폰 기준 다중 Unity 프로젝트 워크플로우

## 목표

- 프로젝트가 없어도 원격으로 생성
- 여러 프로젝트를 등록해두고 필요할 때 전환
- iPhone에서 명령만으로 프로젝트별 작업

## 1) 프로젝트 생성

Unity Worker API:

```bash
curl -X POST "https://<worker-url>/v1/projects/create" \
  -H "Authorization: Bearer <UNITY_WORKER_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name":"MyProjectA",
    "project_path":"",
    "set_active": true
  }'
```

## 2) 프로젝트 목록 조회

```bash
curl -X GET "https://<worker-url>/v1/projects" \
  -H "Authorization: Bearer <UNITY_WORKER_BEARER_TOKEN>"
```

## 3) 활성 프로젝트 전환

```bash
curl -X POST "https://<worker-url>/v1/projects/set-active" \
  -H "Authorization: Bearer <UNITY_WORKER_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name":"MyProjectB",
    "project_path":""
  }'
```

## 4) Cloud Run 통해 프로젝트 지정 실행

```bash
curl -X POST "https://<cloud-run-url>/v1/unity/tasks/run" \
  -H "Authorization: Bearer <REMOTE_API_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id":"req-100",
    "task_type":"ui_add_login_panel",
    "project_name":"MyProjectA",
    "task_payload":{
      "scene":"SampleScene",
      "parent":"Canvas"
    },
    "unity_worker_url":"https://<worker-url>",
    "n8n_webhook_url":"https://<n8n-webhook>"
  }'
```

## 5) GitHub 업로드 자동화 권장 순서

1. 프로젝트 생성
2. `git init`
3. `.gitignore` 적용 (`EXE/mac_automation/setup_project_gitignore.sh`)
4. 원격 저장소 생성 후 push
5. MCP 작업 실행
