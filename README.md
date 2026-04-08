# NewMCP / New-MCP-Unity

MCP 서버·연동 스크립트·웹 대시보드(`web-browser`)·클라우드 게이트웨이 등을 포함한 저장소입니다.  
맥 전원 없이도 클라우드 런타임에서 뉴스→스토리→만화형 슬라이드 파이프라인을 돌릴 수 있도록 **cloud-ready** 엔트리가 포함되어 있습니다.

## 주요 구성

| 경로 | 설명 |
|------|------|
| `MCP_Server/` | MCP 서버 스크립트 (Google 캘린더/시트, Cloud Run 게이트웨이 등) |
| `extensions/` | 단일 목적 확장 스크립트 |
| `collaboration/` | 다중 연동 파이프라인 |
| `common/` | 공용 유틸 (`load_secrets.sh` 포함) |
| `EXE/` | 실행 엔트리 (`run_news_to_comic_ppt.sh`, `start_n8n.sh`, mac 자동화 등) |
| `rules/` | 규칙·패키지 목록·API 키 안내 (시크릿은 커밋하지 않음) |
| `web-browser/` | FastAPI 기반 로컬/배포용 대시보드 |
| `temp/` | 1회성 프롬프트 대응 파일 |

## Cloud-ready 파이프라인 (맥 꺼진 상태)

런타임 시크릿 파일 (택일):

- 권장: `/home/ubuntu/.config/agent-secrets.env`
- 테스트: `temp/agent-secrets.env`

`rules/API_KEYS_NOTE.txt` 참고.

실행:

```bash
bash EXE/run_news_to_comic_ppt.sh
```

확장 스크립트(`extensions/naver_news_to_story.sh` 등)는 자리만 잡혀 있을 수 있으며, 실제 API 호출은 여기에 연결하면 됩니다.

## Git 원격

- 기존: `origin` → [NewMCP](https://github.com/MCP-AI-Acount/NewMCP)
- Unity 연동: `unity` → [New-MCP-Unity](https://github.com/MCP-AI-Acount/New-MCP-Unity)

`~/.cursor/mcp.json` 이 단일 MCP 설정 본체입니다.
