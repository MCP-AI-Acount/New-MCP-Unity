# 쉬운 보안 설정 (3분)

## 1) 키 파일 만들기

```bash
cd "/Users/Windows/Documents/MCP_ Sort/NewMCP"
cp "main rules/.env.example" "main rules/.env.local"
```

`main rules/.env.local` 파일에서 `replace_me` 값만 실제 키로 바꾸면 끝.

## 2) 터미널에 한 번 로드

```bash
cd "/Users/Windows/Documents/MCP_ Sort/NewMCP"
source EXE/mac_automation/load_env.sh
```

## 3) 자동화 설치

```bash
cd "/Users/Windows/Documents/MCP_ Sort/NewMCP"
bash EXE/mac_automation/install_launch_agents.sh
bash EXE/mac_automation/install_sleepwatcher_hooks.sh
```

## 4) 안전 모드 동작

- 자동커밋은 허용 경로만 커밋
- 민감 패턴 감지 시 자동커밋 중단
- 기본값은 자동푸시 OFF

자동푸시 켜려면:

```bash
export AUTO_PUSH=1
```

## 5) 새 프로젝트 추가 시

```bash
bash EXE/mac_automation/setup_project_gitignore.sh "<새 프로젝트 경로>"
```

## 6) 점검

```bash
bash EXE/mac_automation/security_hardening_check.sh
```
