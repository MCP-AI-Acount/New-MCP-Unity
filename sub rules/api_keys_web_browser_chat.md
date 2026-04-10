# web-browser 대시보드 — AI 채팅 답변 API 키

## 어디에 넣나 (둘 다 해당할 수 있음)

| 실행 방식 | 설정 위치 |
|-----------|-----------|
| **로컬** (`uvicorn` 등) | 저장소 루트 `main rules/.env.local` — 서버가 자동 로드 (git 제외) |
| **Cloud Run** (배포 URL) | **반드시** Cloud Run 서비스 **환경 변수** `GEMINI_API_KEY` — Docker 이미지에 `main rules/`가 없어 `.env.local`만으로는 배포에 적용 안 됨 |

키를 새로 받았으면 **로컬용 파일과 Cloud Run 둘 다** 맞춰 줄 것.

---

## 채팅 모드 (사이트 설정)

| 값 | 설명 |
|----|------|
| `gemini` (기본) | `GEMINI_API_KEY` 등으로 API 답변 |
| `cursor_bridge` | Gemini 호출 없이 Cursor용 안내 문구만 자동 추가 (웹훅 선택) |

UI 파일은 서버가 직접 수정하지 않으므로, **Cursor용 복사** 또는 Cursor 연동 모드로 로컬 작업을 이어가면 됩니다.

---

`명령 저장` 시 사용자 메시지 다음에 **AI 답변**을 붙이려면 아래 중 하나가 설정되어 있어야 합니다.

## 필수(택1)

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키. 설정 시 기본으로 OpenAI 사용. |
| `GEMINI_API_KEY` | Google AI Studio / Gemini API 키. OpenAI 키가 없을 때 사용. |

## 선택

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CHAT_AI_PROVIDER` | `auto` | `openai` \| `gemini` \| `auto` \| `none` — `none`이면 AI 호출 안 함. |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 채팅 모델 이름. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini 모델 이름. `gemini-1.5-flash` 등 구버전은 404가 나므로 쓰지 말 것. |

## Cloud Run 예시

```bash
gcloud run services update web-browser-dashboard \
  --region asia-northeast3 \
  --set-secrets "OPENAI_API_KEY=openai-key:latest"
# 또는 --set-env-vars OPENAI_API_KEY=sk-...
```

비용·쿼터는 각 제공자 정책을 따릅니다.
