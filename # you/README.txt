[# you] 비밀값 저장 안내

이 폴더는 API 키/토큰 같은 비밀값을 저장하는 전용 위치입니다.
아래 파일을 수정하면 연동 스크립트들이 자동으로 읽어 적용합니다.

1) 수정 파일
- /workspace/# you/keys.env

2) 기본 형식
- KEY=VALUE
- 줄 시작 # 은 주석

3) 예시
- GITHUB_TOKEN=ghp_xxx
- REMOTE_API_BEARER_TOKEN=xxx
- UNITY_WORKER_BEARER_TOKEN=xxx
- OPENAI_API_KEY=sk-xxx

4) 보안
- 이 폴더와 파일은 .gitignore에 등록되어 Git에 올라가지 않게 설정되어 있습니다.
- 비밀값은 절대 커밋하지 마세요.

