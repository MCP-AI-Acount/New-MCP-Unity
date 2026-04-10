#!/usr/bin/env python3
import json
import os
import random
import subprocess
import threading
import time
from datetime import datetime
from typing import Any, Dict, List
from urllib import error, parse, request

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATIC_DIR = os.path.join(ROOT, "static")
_REPO_ROOT = os.path.dirname(ROOT)


def _load_env_file(path: str) -> None:
  if not os.path.isfile(path):
    return
  with open(path, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      if "=" not in line:
        continue
      k, _, v = line.partition("=")
      k, v = k.strip(), v.strip().strip('"').strip("'")
      if k and k not in os.environ:
        os.environ[k] = v


_load_env_file(os.path.join(_REPO_ROOT, "main rules", ".env.local"))
_load_env_file(os.path.join(ROOT, ".env"))

SESSIONS_FILE = os.path.join(DATA_DIR, "chat_sessions.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")
QUEUE_FILE = os.path.join(DATA_DIR, "command_queue.json")
SITE_CONFIG_FILE = os.path.join(DATA_DIR, "site_config.json")
CURSOR_RULES_FILE = os.environ.get(
  "CURSOR_RULES_FILE", os.path.join(_REPO_ROOT, ".cursor", "rules", "cursor_top_rules.md")
)
WEB_CURSOR_RULES_FILE = os.path.join(DATA_DIR, "cursor_top_rules.md")
RULES_SYNC_INTERVAL_SECONDS = max(1, int(os.environ.get("RULES_SYNC_INTERVAL_SECONDS", "2") or "2"))


class _DashboardStore:
  def __init__(self) -> None:
    self._lock = threading.Lock()
    self._backend = "file"
    self._firestore_client = None
    self._collection = os.environ.get("WEB_STORE_COLLECTION", "web_dashboard_state")
    mode = (os.environ.get("WEB_STORE_MODE", "auto") or "auto").strip().lower()
    if mode == "file":
      return
    try:
      from google.cloud import firestore  # type: ignore

      project_id = (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or os.environ.get("PROJECT_ID")
        or ""
      )
      self._firestore_client = firestore.Client(project=project_id or None)
      self._backend = "firestore"
    except Exception:
      self._firestore_client = None
      self._backend = "file"

  @property
  def backend(self) -> str:
    return self._backend

  @staticmethod
  def _key_from_path(path: str) -> str:
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    return name or base or "unknown"

  def _read_file_json(self, path: str, default: Any) -> Any:
    if not os.path.isfile(path):
      return default
    with self._lock:
      try:
        with open(path, encoding="utf-8") as f:
          return json.load(f)
      except Exception:
        return default

  def _write_file_json(self, path: str, data: Any) -> None:
    parent = os.path.dirname(path)
    if parent:
      os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.tmp-{os.getpid()}-{threading.get_ident()}"
    with self._lock:
      with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
      os.replace(tmp_path, path)

  def read_json(self, path: str, default: Any) -> Any:
    if self._firestore_client is not None:
      try:
        key = self._key_from_path(path)
        snap = self._firestore_client.collection(self._collection).document(key).get()
        if snap.exists:
          payload = snap.to_dict() or {}
          if "value" in payload:
            return payload["value"]
      except Exception:
        pass
    return self._read_file_json(path, default)

  def write_json(self, path: str, data: Any) -> None:
    if self._firestore_client is not None:
      try:
        key = self._key_from_path(path)
        self._firestore_client.collection(self._collection).document(key).set(
          {
            "key": key,
            "value": data,
            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          }
        )
      except Exception:
        pass
    self._write_file_json(path, data)


_STORE = _DashboardStore()
_rules_sync_last_signature = ""
_rules_sync_thread_started = False
_rules_sync_thread_lock = threading.Lock()


def _rules_signature() -> str:
  targets = _rules_sync_targets()
  parts: List[str] = []
  for path in targets:
    if not path:
      continue
    mtime = _safe_mtime(path)
    size = -1
    try:
      size = os.path.getsize(path)
    except OSError:
      size = -1
    parts.append(f"{path}|{mtime}|{size}")
  return "||".join(parts)


def _rules_sync_if_changed(force: bool = False) -> Dict[str, Any]:
  global _rules_sync_last_signature
  current_signature = _rules_signature()
  if not force and current_signature == _rules_sync_last_signature:
    return {
      "changed": False,
      "sourcePath": "",
      "writtenPaths": [],
      "content": "",
    }
  synced = _sync_rules_files()
  _rules_sync_last_signature = _rules_signature()
  synced["changed"] = True
  return synced


def _rules_sync_daemon() -> None:
  while True:
    try:
      _rules_sync_if_changed(force=False)
    except Exception:
      pass
    time.sleep(RULES_SYNC_INTERVAL_SECONDS)


def _start_rules_sync_background() -> None:
  global _rules_sync_thread_started
  with _rules_sync_thread_lock:
    if _rules_sync_thread_started:
      return
    # Uvicorn reload/worker 환경에서도 중복 실행 영향을 최소화하기 위해 daemon thread 사용.
    thread = threading.Thread(target=_rules_sync_daemon, name="rules-sync-daemon", daemon=True)
    thread.start()
    _rules_sync_thread_started = True


def _read_json(path: str, default: Any) -> Any:
  return _STORE.read_json(path, default)


def _write_json(path: str, data: Any) -> None:
  _STORE.write_json(path, data)


def _read_text(path: str, default: str = "") -> str:
  if not os.path.isfile(path):
    return default
  try:
    with open(path, encoding="utf-8") as f:
      return f.read()
  except OSError:
    return default


def _write_text(path: str, content: str) -> bool:
  try:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
      f.write(content)
    return True
  except OSError:
    return False


def _rules_sync_targets() -> List[str]:
  raw = [
    CURSOR_RULES_FILE,
    os.path.join(_REPO_ROOT, ".cursor", "rules", "cursor_top_rules.md"),
    WEB_CURSOR_RULES_FILE,
  ]
  out: List[str] = []
  for path in raw:
    if path and path not in out:
      out.append(path)
  return out


def _safe_mtime(path: str) -> float:
  try:
    return os.path.getmtime(path)
  except OSError:
    return -1.0


def _sync_rules_files() -> Dict[str, Any]:
  targets = _rules_sync_targets()
  existing = [p for p in targets if os.path.isfile(p)]
  source_path = max(existing, key=_safe_mtime) if existing else targets[0]
  content = _read_text(source_path, "") if source_path else ""
  written_paths: List[str] = []
  for path in targets:
    if not path:
      continue
    if _write_text(path, content):
      written_paths.append(path)
  return {
    "sourcePath": source_path,
    "writtenPaths": written_paths,
    "content": content,
  }


def _site_config() -> Dict[str, Any]:
  return _read_json(SITE_CONFIG_FILE, {})


def _effective_setting(key: str, env_key: str, default: str = "") -> str:
  cfg = _site_config()
  v = str(cfg.get(key) or "").strip()
  if v:
    return v
  return str(os.environ.get(env_key, default) or "").strip()


def _compute_progress(
  session_id: str,
  queue_items: List[Dict[str, Any]],
  st: Dict[str, Any],
) -> Dict[str, Any]:
  now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  sid = (session_id or "").strip()
  filtered = [q for q in queue_items if not sid or q.get("sessionId") == sid]
  failed = [q for q in filtered if q.get("status") == "failed"]
  queued = [q for q in filtered if q.get("status") == "queued"]
  sent = [q for q in filtered if q.get("status") == "sent"]
  sorted_q = sorted(filtered, key=lambda x: str(x.get("createdAt", "")), reverse=True)

  webhook_ok = bool(_effective_setting("n8nCommandWebhookUrl", "N8N_COMMAND_WEBHOOK_URL", ""))
  if failed:
    q_summary = f"실패 {len(failed)}건 — 점검 필요"
    q_ok = False
  elif sent:
    q_summary = f"전송됨 {len(sent)}건 (응답·완료 대기)"
    q_ok = True
  elif queued:
    q_summary = f"대기 {len(queued)}건"
    q_ok = webhook_ok
  else:
    q_summary = "이 세션 큐에 항목 없음"
    q_ok = True

  q_lines: List[str] = [
    f"n8n 웹훅: {'설정됨' if webhook_ok else '미설정 (전송 불가)'}",
  ]
  for q in sorted_q[:6]:
    cmd = str(q.get("command", ""))[:96]
    extra = q.get("resultMessage") or q.get("error") or ""
    line = f"[{q.get('status', '?')}] {cmd}"
    if extra:
      line += f" — {str(extra)[:80]}"
    q_lines.append(line)

  cr = st.get("cloudRun") or "Cloud Run: 확인 안 됨"
  uw = st.get("unityWorker") or "Unity Worker: 확인 안 됨"
  cr_bad = "down" in cr.lower() or "unknown" in cr.lower()
  uw_bad = "down" in uw.lower() or "unknown" in uw.lower()
  if cr_bad or uw_bad:
    s_summary = "일부 서비스 응답 불가 또는 미확인"
    s_ok = False
  else:
    s_summary = "헬스 체크 기준 정상"
    s_ok = True
  s_lines = [cr, uw]

  url = (st.get("latestScreenshotUrl") or "").strip()
  if url:
    ss_summary = "최신 스크린샷 있음"
    ss_ok = True
    ss_lines = [url[:120] + ("…" if len(url) > 120 else "")]
  else:
    ss_summary = "스크린샷 없음 (완료·캡처 후 표시)"
    ss_ok = True
    ss_lines = []

  dbg = (st.get("debugSummary") or "").strip() or "요약 없음"
  d_ok = "오류" not in dbg and "실패" not in dbg
  d_lines = [dbg[:200]]

  ai_on = bool(os.environ.get("OPENAI_API_KEY", "").strip() or os.environ.get("GEMINI_API_KEY", "").strip())
  hints: List[str] = []
  if ai_on:
    hints.append(
      "「명령 저장」 시 OPENAI/Gemini로 AI 답변이 같은 세션에 이어 붙습니다. 유니티·n8n 실행과는 별개입니다."
    )
  else:
    hints.append(
      "AI 답변을 받으려면 서버에 OPENAI_API_KEY 또는 GEMINI_API_KEY 를 설정하세요. "
      "설정 전에는 채팅이 로그로만 저장됩니다."
    )
  hints.append(
    "n8n·워커로 보내려면 「스택 열기」→ 줄 단위 명령 → 「스택 저장」→ 「다음 명령 실행」 순서가 필요합니다."
  )
  hints.append("웹훅·헬스 URL·프로젝트 이름·페이지 제목은 좌측 「사이트」에서 바꿀 수 있습니다. (서버에 저장, 환경 변수보다 우선)")
  if not webhook_ok:
    hints.append("N8N_COMMAND_WEBHOOK_URL 이 서버(Cloud Run) 환경변수에 없으면 외부로 명령을 보낼 수 없습니다.")

  return {
    "serverTime": now,
    "sessionId": sid,
    "hints": hints,
    "queue": {"summary": q_summary, "lines": q_lines, "ok": q_ok},
    "service": {"summary": s_summary, "lines": s_lines, "ok": s_ok},
    "screenshot": {"summary": ss_summary, "lines": ss_lines, "ok": ss_ok},
    "debug": {"summary": dbg[:120], "lines": d_lines, "ok": d_ok},
  }


def _get_url_json(url: str, timeout: int = 10) -> Dict[str, Any]:
  try:
    with request.urlopen(url, timeout=timeout) as resp:
      body = resp.read().decode("utf-8", errors="ignore")
      return {"ok": True, "status": resp.status, "body": body}
  except error.HTTPError as e:
    return {"ok": False, "status": e.code, "body": ""}
  except Exception:
    return {"ok": False, "status": 0, "body": ""}


def _run_cmd(args: List[str], timeout: int = 8) -> Dict[str, Any]:
  try:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return {
      "ok": proc.returncode == 0,
      "returncode": proc.returncode,
      "stdout": (proc.stdout or "").strip(),
      "stderr": (proc.stderr or "").strip(),
    }
  except Exception as e:
    return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(e)}


def _git_runtime_status() -> Dict[str, Any]:
  git_dir = os.path.join(_REPO_ROOT, ".git")
  if not os.path.isdir(git_dir):
    return {"available": False, "branch": "-", "lastCommit": "-", "dirty": False}

  branch_out = _run_cmd(["git", "-C", _REPO_ROOT, "branch", "--show-current"])
  commit_out = _run_cmd(["git", "-C", _REPO_ROOT, "log", "--oneline", "-n", "1"])
  dirty_out = _run_cmd(["git", "-C", _REPO_ROOT, "status", "--porcelain"])
  return {
    "available": True,
    "branch": branch_out["stdout"] or "-",
    "lastCommit": commit_out["stdout"] or "-",
    "dirty": bool(dirty_out["stdout"]),
  }


def _runtime_snapshot(status: Dict[str, Any]) -> Dict[str, Any]:
  return {
    "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "storeBackend": _STORE.backend,
    "vmPolicy": "idle 5분(300초) 무입력 시 자동 중지 목표",
    "cloudRunGateway": "Cloud Run Gateway: healthy",
    "cloudRunTarget": status.get("cloudRun") or "Cloud Run: unknown",
    "unityWorker": status.get("unityWorker") or "Unity Worker: unknown",
    "n8n": (status.get("n8n") or {}).get("lastResult", "unknown"),
    "git": _git_runtime_status(),
  }


def _queue_status_bucket(raw_status: str) -> str:
  s = (raw_status or "").strip().lower()
  if s in {"queued", "pending"}:
    return "queued"
  if s in {"sent", "running", "in_progress"}:
    return "running"
  if s in {"success", "completed", "done", "ok"}:
    return "success"
  if s in {"failed", "error"}:
    return "failed"
  return "unknown"


def _classify_command_flow(command_text: str) -> str:
  c = (command_text or "").strip().lower()
  if any(k in c for k in ["unity", "sample", "scene", "graph", "play_and_capture", "reportmaker"]):
    return "unity-vm"
  if any(k in c for k in ["git ", " onepush", "onepush", "push", "pull", "commit", "branch"]):
    return "git-sync"
  return "general"


def _pick_current_queue_item(queue_items: List[Dict[str, Any]]) -> Dict[str, Any]:
  def _sort_key(x: Dict[str, Any]) -> str:
    return str(x.get("createdAt", ""))

  running = [x for x in queue_items if _queue_status_bucket(str(x.get("status", ""))) == "running"]
  if running:
    return sorted(running, key=_sort_key, reverse=True)[0]

  queued = [x for x in queue_items if _queue_status_bucket(str(x.get("status", ""))) == "queued"]
  if queued:
    return sorted(queued, key=_sort_key, reverse=True)[0]

  if queue_items:
    return sorted(queue_items, key=_sort_key, reverse=True)[0]

  return {}


def _pipeline_state(status: Dict[str, Any], queue_items: List[Dict[str, Any]]) -> Dict[str, Any]:
  current = _pick_current_queue_item(queue_items)
  command_text = str(current.get("command", ""))
  raw_status = str(current.get("status", ""))
  bucket = _queue_status_bucket(raw_status)
  flow = _classify_command_flow(command_text)

  nodes = [
    {"id": "command", "label": "명령 입력", "state": "idle"},
    {"id": "cursor", "label": "Cursor Cloud", "state": "idle"},
    {"id": "cloudrun", "label": "Cloud Run", "state": "idle"},
    {"id": "vm", "label": "VM Worker", "state": "idle"},
    {"id": "git", "label": "Git 동기화", "state": "idle"},
  ]
  node_map = {x["id"]: x for x in nodes}

  current_stage = "idle"
  belongs_to = "일반"
  if flow == "unity-vm":
    belongs_to = "Unity/VM"
  elif flow == "git-sync":
    belongs_to = "Git"

  if current:
    node_map["command"]["state"] = "success"
    if bucket == "queued":
      node_map["cursor"]["state"] = "running"
      node_map["cloudrun"]["state"] = "pending"
      node_map["vm"]["state"] = "pending" if flow == "unity-vm" else "idle"
      node_map["git"]["state"] = "pending" if flow == "git-sync" else "idle"
      current_stage = "cursor"
    elif bucket == "running":
      node_map["cursor"]["state"] = "success"
      node_map["cloudrun"]["state"] = "running"
      if flow == "unity-vm":
        node_map["vm"]["state"] = "running"
        current_stage = "vm"
      elif flow == "git-sync":
        node_map["git"]["state"] = "running"
        current_stage = "git"
      else:
        current_stage = "cloudrun"
    elif bucket == "success":
      node_map["cursor"]["state"] = "success"
      node_map["cloudrun"]["state"] = "success"
      if flow == "unity-vm":
        node_map["vm"]["state"] = "success"
      if flow == "git-sync":
        node_map["git"]["state"] = "success"
      current_stage = "done"
    elif bucket == "failed":
      node_map["cursor"]["state"] = "success"
      node_map["cloudrun"]["state"] = "failed"
      if flow == "unity-vm":
        node_map["vm"]["state"] = "failed"
        current_stage = "vm"
      elif flow == "git-sync":
        node_map["git"]["state"] = "failed"
        current_stage = "git"
      else:
        current_stage = "cloudrun"

  cloud_run_down = "down" in str(status.get("cloudRun", "")).lower()
  vm_down = "down" in str(status.get("unityWorker", "")).lower()
  if cloud_run_down and node_map["cloudrun"]["state"] in {"running", "pending", "idle"}:
    node_map["cloudrun"]["state"] = "failed"
  if vm_down and flow == "unity-vm" and node_map["vm"]["state"] in {"running", "pending", "idle"}:
    node_map["vm"]["state"] = "failed"

  return {
    "currentCommand": command_text,
    "rawStatus": raw_status,
    "statusBucket": bucket,
    "belongsTo": belongs_to,
    "currentStage": current_stage,
    "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "storeBackend": _STORE.backend,
    "nodes": nodes,
  }


def _stage_label(stage: str) -> str:
  mapping = {
    "idle": "대기",
    "cursor": "Cursor Cloud",
    "cloudrun": "Cloud Run",
    "vm": "VM Worker",
    "git": "Git 동기화",
    "done": "완료",
  }
  return mapping.get(stage, stage or "-")


app = FastAPI(title="remote-dev-web-browser")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


class ClipboardPermissionsMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    response = await call_next(request)
    response.headers["Permissions-Policy"] = "clipboard-write=(self), clipboard-read=(self)"
    return response


app.add_middleware(ClipboardPermissionsMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def _startup_rules_sync() -> None:
  _rules_sync_if_changed(force=True)
  _start_rules_sync_background()


class MessageIn(BaseModel):
  sessionId: str
  role: str
  text: str


class StackIn(BaseModel):
  sessionId: str
  rawText: str = ""


class AckIn(BaseModel):
  queueId: str
  status: str
  message: str = ""
  screenshotUrl: str = ""


class SessionCreate(BaseModel):
  title: str = "새 채팅"


class RulesUpdate(BaseModel):
  content: str = ""


class SiteConfigIn(BaseModel):
  siteTitle: str = ""
  activeProjectName: str = ""
  n8nCommandWebhookUrl: str = ""
  n8nStatusUrl: str = ""
  cloudRunHealthUrl: str = ""
  unityWorkerHealthUrl: str = ""
  chatAssistantMode: str = "gemini"
  cursorBridgeWebhookUrl: str = ""


def _append_message(session_id: str, role: str, text: str) -> None:
  messages = _read_json(MESSAGES_FILE, [])
  messages.append({"sessionId": session_id, "role": role, "text": text})
  _write_json(MESSAGES_FILE, messages)


def _touch_session(session_id: str) -> None:
  sessions = _read_json(SESSIONS_FILE, [])
  for s in sessions:
    if s.get("id") == session_id:
      s["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
  _write_json(SESSIONS_FILE, sessions)


def _system_prompt_for_chat() -> str:
  base = (
    "당신은 이 저장소의 「원격 개발 대시보드」(web-browser: FastAPI + 정적 HTML/CSS/JS)를 돕는 기술 어시스턴트입니다. "
    "항상 한국어로 답합니다.\n\n"
    "【중요】 사용자가 UI·화면·레이아웃·스타일·버튼·탭 등을 바꾸고 싶다고 하면 절대 거절하지 마세요. "
    "「실제 화면을 직접 조작할 수 없다」는 식의 면책 문구로 답하지 마세요. "
    "대신 다음을 반드시 수행하세요: 수정할 파일 경로(예: web-browser/static/index.html, styles.css, app.js)를 명시하고, "
    "붙여넣을 수 있는 HTML/CSS/JS 조각, 또는 검색·교체할 코드 블록을 구체적으로 제시하세요. "
    "이 앱에는 이미 좌측 「사이트」 메뉴로 제목·웹훅·헬스 URL 등을 웹에서 저장하는 기능이 있음을 필요할 때 짧게 안내할 수 있습니다.\n\n"
    "배포(Cursor, git, Cloud Run)는 사용자 환경에 맡기고, 당신은 코드와 단계만 명확히 제공하면 됩니다.\n"
    "이 Cloud Run 프로세스는 저장소 파일을 쓰지 못한다는 점은 사용자가 「Cursor용 복사」로 로컬에서 수정하는 흐름과 모순되지 않는다."
  )
  if os.path.isfile(CURSOR_RULES_FILE):
    try:
      with open(CURSOR_RULES_FILE, encoding="utf-8") as f:
        rules = f.read(12000)
      if rules.strip():
        base += "\n\n[사용자 규칙]\n" + rules
    except OSError:
      pass
  return base


def _session_messages_for_llm(session_id: str) -> List[Dict[str, str]]:
  allm = _read_json(MESSAGES_FILE, [])
  sess = [m for m in allm if m.get("sessionId") == session_id]
  out: List[Dict[str, str]] = []
  for m in sess[-40:]:
    r = m.get("role", "user")
    t = str(m.get("text", ""))
    if r == "user":
      out.append({"role": "user", "content": t})
    elif r == "assistant":
      out.append({"role": "assistant", "content": t})
    else:
      out.append({"role": "user", "content": "[시스템 로그]\n" + t})
  return out


def _call_openai_chat(api_key: str, model: str, messages: List[Dict[str, str]]) -> str:
  payload = json.dumps(
    {
      "model": model,
      "messages": [{"role": "system", "content": _system_prompt_for_chat()}, *messages],
      "max_tokens": 2048,
      "temperature": 0.6,
    },
    ensure_ascii=False,
  ).encode("utf-8")
  req = request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=payload,
    headers={
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}",
    },
    method="POST",
  )
  with request.urlopen(req, timeout=120) as resp:
    data = json.loads(resp.read().decode("utf-8"))
  return str(data["choices"][0]["message"]["content"]).strip()


def _merge_gemini_turns(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
  """Gemini REST는 user/model이 번갈아야 해서, 같은 역할이 연속이면 한 턴으로 합친다."""
  out: List[Dict[str, str]] = []
  for m in messages:
    role = m.get("role", "user")
    content = str(m.get("content", ""))
    side = "assistant" if role == "assistant" else "user"
    if out and out[-1]["_side"] == side:
      out[-1]["content"] += "\n\n" + content
    else:
      out.append({"_side": side, "role": role, "content": content})
  for o in out:
    o.pop("_side", None)
  return out


def _call_gemini_chat(api_key: str, model: str, messages: List[Dict[str, str]]) -> str:
  merged = _merge_gemini_turns(messages)
  system_text = _system_prompt_for_chat()
  contents: List[Dict[str, Any]] = []
  for m in merged:
    role = m["role"]
    content = m["content"]
    if role == "assistant":
      contents.append({"role": "model", "parts": [{"text": content}]})
    else:
      contents.append({"role": "user", "parts": [{"text": content}]})
  body = json.dumps(
    {
      "systemInstruction": {"parts": [{"text": system_text}]},
      "contents": contents,
      "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2048},
    },
    ensure_ascii=False,
  ).encode("utf-8")
  key_q = parse.quote(api_key, safe="")
  url = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{model}:generateContent?key={key_q}"
  )
  req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
  try:
    with request.urlopen(req, timeout=120) as resp:
      data = json.loads(resp.read().decode("utf-8"))
  except error.HTTPError as e:
    err_body = e.read().decode("utf-8", errors="ignore")[:1200]
    raise ValueError(f"Gemini HTTP {e.code}: {err_body}") from e
  candidates = data.get("candidates") or []
  if not candidates:
    raise ValueError("Gemini 응답이 비어 있습니다.")
  parts = candidates[0].get("content", {}).get("parts") or []
  texts = [p.get("text", "") for p in parts]
  return "".join(texts).strip()


def _try_chat_ai_reply(session_id: str) -> str:
  openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
  gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
  provider = os.environ.get("CHAT_AI_PROVIDER", "auto").strip().lower()
  if provider == "none":
    return ""
  if provider == "openai" and not openai_key:
    return ""
  if provider == "gemini" and not gemini_key:
    return ""
  if provider == "auto" and not openai_key and not gemini_key:
    return ""
  msgs = _session_messages_for_llm(session_id)
  if not msgs:
    return ""
  try:
    if provider == "gemini":
      model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
      return _call_gemini_chat(gemini_key, model, msgs)
    if provider == "openai":
      model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
      return _call_openai_chat(openai_key, model, msgs)
    if openai_key:
      model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
      return _call_openai_chat(openai_key, model, msgs)
    if gemini_key:
      model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
      return _call_gemini_chat(gemini_key, model, msgs)
  except Exception as e:
    return f"(AI 응답 실패: {e})"
  return ""


def _cursor_bridge_reply_text(user_text: str) -> str:
  return (
    "[웹 대시보드 → Cursor 연동]\n"
    "이 사이트(Cloud Run)는 Git 저장소 파일을 직접 수정하지 않습니다. "
    "UI를 바꾸려면 아래 블록 전체를 복사해 **로컬 Cursor 채팅**에 붙여 넣어 에이전트가 코드를 수정하게 하세요.\n\n"
    "【요청】\n"
    + user_text
    + "\n\n【우선 볼 경로】\n"
    "- web-browser/static/index.html\n"
    "- web-browser/static/styles.css\n"
    "- web-browser/static/app.js\n"
    "- web-browser/server.py"
  )


def _post_cursor_bridge_webhook(session_id: str, user_text: str) -> None:
  url = str(_site_config().get("cursorBridgeWebhookUrl") or "").strip()
  if not url:
    return
  try:
    payload = json.dumps(
      {"sessionId": session_id, "text": user_text, "source": "web-browser-dashboard"},
      ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
      url,
      data=payload,
      headers={"Content-Type": "application/json"},
      method="POST",
    )
    with request.urlopen(req, timeout=15) as resp:
      resp.read()
  except Exception:
    pass


@app.get("/")
def index():
  return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/chat/sessions")
def get_sessions() -> List[Dict[str, Any]]:
  return _read_json(SESSIONS_FILE, [])


@app.get("/api/chat/messages")
def get_messages() -> List[Dict[str, Any]]:
  return _read_json(MESSAGES_FILE, [])


@app.get("/api/cursor-prompt")
def cursor_prompt(text: str = Query(default="", alias="text")) -> Dict[str, str]:
  return {"prompt": _cursor_bridge_reply_text(text)}


@app.post("/api/chat/messages")
def add_message(message: MessageIn) -> Dict[str, Any]:
  _append_message(message.sessionId, message.role, message.text)
  _touch_session(message.sessionId)
  reply = ""
  assistant_mode = ""
  if message.role == "user":
    mode = (_site_config().get("chatAssistantMode") or "gemini").strip()
    if mode not in ("gemini", "cursor_bridge"):
      mode = "gemini"
    assistant_mode = mode
    if mode == "cursor_bridge":
      reply = _cursor_bridge_reply_text(message.text)
      _post_cursor_bridge_webhook(message.sessionId, message.text)
      _append_message(message.sessionId, "assistant", reply)
      _touch_session(message.sessionId)
    else:
      reply = _try_chat_ai_reply(message.sessionId)
      if reply:
        _append_message(message.sessionId, "assistant", reply)
        _touch_session(message.sessionId)
  return {"ok": True, "reply": reply or None, "assistantMode": assistant_mode or None}


@app.post("/api/chat/sessions")
def create_session(body: SessionCreate) -> Dict[str, Any]:
  sid = f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
  sessions = _read_json(SESSIONS_FILE, [])
  sessions.append(
    {
      "id": sid,
      "title": body.title,
      "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
  )
  _write_json(SESSIONS_FILE, sessions)
  return {"ok": True, "session": sessions[-1]}


@app.delete("/api/chat/sessions/{session_id}")
def delete_session(session_id: str) -> Dict[str, Any]:
  sessions = _read_json(SESSIONS_FILE, [])
  sessions = [s for s in sessions if s.get("id") != session_id]
  _write_json(SESSIONS_FILE, sessions)
  messages = _read_json(MESSAGES_FILE, [])
  messages = [m for m in messages if m.get("sessionId") != session_id]
  _write_json(MESSAGES_FILE, messages)
  return {"ok": True}


@app.get("/api/rules")
def get_rules() -> Dict[str, Any]:
  synced = _rules_sync_if_changed(force=False)
  if not synced.get("changed"):
    synced = _sync_rules_files()
  return {
    "content": synced.get("content", ""),
    "path": CURSOR_RULES_FILE,
    "sourcePath": synced.get("sourcePath", ""),
    "syncedPaths": synced.get("writtenPaths", []),
  }


@app.put("/api/rules")
def put_rules(body: RulesUpdate) -> Dict[str, Any]:
  global _rules_sync_last_signature
  written_paths: List[str] = []
  for path in _rules_sync_targets():
    if path and _write_text(path, body.content):
      written_paths.append(path)
  _rules_sync_last_signature = _rules_signature()
  if not written_paths:
    raise HTTPException(status_code=500, detail="규칙 파일 저장에 실패했습니다.")
  return {"ok": True, "path": CURSOR_RULES_FILE, "syncedPaths": written_paths}


@app.get("/api/site-config")
def get_site_config() -> Dict[str, Any]:
  cfg = _site_config()
  defaults = {
    "siteTitle": "원격 개발 대시보드",
    "activeProjectName": "",
    "n8nCommandWebhookUrl": "",
    "n8nStatusUrl": "",
    "cloudRunHealthUrl": "",
    "unityWorkerHealthUrl": "",
    "chatAssistantMode": "gemini",
    "cursorBridgeWebhookUrl": "",
  }
  merged = {**defaults, **cfg}
  return merged


@app.put("/api/site-config")
def put_site_config(body: SiteConfigIn) -> Dict[str, Any]:
  mode = (body.chatAssistantMode or "gemini").strip()
  if mode not in ("gemini", "cursor_bridge"):
    mode = "gemini"
  data = {
    "siteTitle": body.siteTitle,
    "activeProjectName": body.activeProjectName,
    "n8nCommandWebhookUrl": body.n8nCommandWebhookUrl,
    "n8nStatusUrl": body.n8nStatusUrl,
    "cloudRunHealthUrl": body.cloudRunHealthUrl,
    "unityWorkerHealthUrl": body.unityWorkerHealthUrl,
    "chatAssistantMode": mode,
    "cursorBridgeWebhookUrl": body.cursorBridgeWebhookUrl,
  }
  _write_json(SITE_CONFIG_FILE, data)
  return {"ok": True, "config": data}


@app.get("/api/status")
def get_status(
  include_services: bool = Query(default=False),
  include_n8n: bool = Query(default=False),
  session_id: str = Query(default="", alias="sessionId"),
) -> Dict[str, Any]:
  status = _read_json(STATUS_FILE, {})
  cfg_proj = _effective_setting("activeProjectName", "UNITY_ACTIVE_PROJECT_NAME", "")
  status["activeProject"] = cfg_proj if cfg_proj else status.get("activeProject", "-")
  queue_items = _read_json(QUEUE_FILE, [])
  queued = len([q for q in queue_items if q.get("status") == "queued"])
  running = len([q for q in queue_items if q.get("status") == "sent"])
  status["queue"] = {"queued": queued, "sent": running, "total": len(queue_items)}

  if include_services:
    cloud_run_health_url = _effective_setting("cloudRunHealthUrl", "CLOUD_RUN_HEALTH_URL", "")
    unity_worker_health_url = _effective_setting("unityWorkerHealthUrl", "UNITY_WORKER_HEALTH_URL", "")
    if cloud_run_health_url:
      res = _get_url_json(cloud_run_health_url)
      status["cloudRun"] = f"Cloud Run: {'healthy' if res['ok'] else 'down'}"
    if unity_worker_health_url:
      res = _get_url_json(unity_worker_health_url)
      status["unityWorker"] = f"Unity Worker: {'healthy' if res['ok'] else 'down'}"

  if include_n8n:
    n8n_status_url = _effective_setting("n8nStatusUrl", "N8N_STATUS_URL", "")
    if n8n_status_url:
      res = _get_url_json(n8n_status_url)
      status.setdefault("n8n", {})
      status["n8n"]["lastResult"] = "success" if res["ok"] else "failed"
      status["n8n"]["lastTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")

  status["progress"] = _compute_progress(session_id, queue_items, status)

  if not status:
    raise HTTPException(status_code=500, detail="status data not found")
  return status


@app.get("/api/queue")
def get_queue() -> List[Dict[str, Any]]:
  return _read_json(QUEUE_FILE, [])


@app.post("/api/queue/stack")
def stack_queue(body: StackIn) -> Dict[str, Any]:
  commands = [line.strip() for line in body.rawText.splitlines() if line.strip()]
  if not commands:
    raise HTTPException(status_code=400, detail="명령이 비어 있습니다.")
  queue_items = _read_json(QUEUE_FILE, [])
  now = datetime.now().strftime("%Y%m%d%H%M%S")
  for idx, cmd in enumerate(commands):
    queue_items.append(
      {
        "id": f"q-{now}-{idx}",
        "sessionId": body.sessionId,
        "command": cmd,
        "status": "queued",
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      }
    )
  _write_json(QUEUE_FILE, queue_items)
  _append_message(body.sessionId, "system", f"명령 {len(commands)}개를 스택에 추가했습니다.")
  _touch_session(body.sessionId)
  return {"ok": True, "added": len(commands)}


@app.post("/api/queue/dispatch-next")
def dispatch_next() -> Dict[str, Any]:
  webhook_url = _effective_setting("n8nCommandWebhookUrl", "N8N_COMMAND_WEBHOOK_URL", "")
  if not webhook_url:
    raise HTTPException(
      status_code=400,
      detail="n8n 명령 웹훅 URL이 필요합니다. 사이트 설정 또는 N8N_COMMAND_WEBHOOK_URL 환경 변수를 설정하세요.",
    )

  queue_items = _read_json(QUEUE_FILE, [])
  target = next((q for q in queue_items if q.get("status") == "queued"), None)
  if not target:
    return {"ok": True, "message": "대기중인 명령이 없습니다."}

  payload = json.dumps(
    {
      "queueId": target["id"],
      "sessionId": target["sessionId"],
      "command": target["command"],
    }
  ).encode("utf-8")
  req = request.Request(
    url=webhook_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
  )
  try:
    with request.urlopen(req, timeout=20) as resp:
      _ = resp.read()
    target["status"] = "sent"
    target["sentAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_message(target["sessionId"], "system", f"n8n로 명령 전송: {target['command']}")
  except Exception as e:
    target["status"] = "failed"
    target["error"] = str(e)
    _append_message(target["sessionId"], "system", f"전송 실패: {target['command']}")
  _write_json(QUEUE_FILE, queue_items)
  _touch_session(target["sessionId"])
  return {"ok": True, "queueId": target["id"], "status": target["status"]}


@app.post("/api/queue/ack")
def ack_queue(body: AckIn) -> Dict[str, Any]:
  queue_items = _read_json(QUEUE_FILE, [])
  target = next((q for q in queue_items if q.get("id") == body.queueId), None)
  if not target:
    raise HTTPException(status_code=404, detail="queue item not found")
  target["status"] = body.status
  target["ackAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  if body.message:
    target["resultMessage"] = body.message
  if body.screenshotUrl:
    target["screenshotUrl"] = body.screenshotUrl

  _append_message(target["sessionId"], "system", f"[{body.status}] {target['command']} {body.message}".strip())
  _touch_session(target["sessionId"])
  _write_json(QUEUE_FILE, queue_items)

  status = _read_json(STATUS_FILE, {})
  status.setdefault("n8n", {})
  status["n8n"]["lastResult"] = body.status
  status["n8n"]["lastTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")
  if body.screenshotUrl:
    status["latestScreenshotUrl"] = body.screenshotUrl
  _write_json(STATUS_FILE, status)
  return {"ok": True}


@app.get("/api/runtime-snapshot")
def runtime_snapshot(include_services: bool = Query(default=True), include_n8n: bool = Query(default=True)) -> Dict[str, Any]:
  status = _read_json(STATUS_FILE, {})
  if include_services:
    cloud_run_health_url = _effective_setting("cloudRunHealthUrl", "CLOUD_RUN_HEALTH_URL", "")
    unity_worker_health_url = _effective_setting("unityWorkerHealthUrl", "UNITY_WORKER_HEALTH_URL", "")
    if cloud_run_health_url:
      res = _get_url_json(cloud_run_health_url)
      status["cloudRun"] = f"Cloud Run: {'healthy' if res['ok'] else 'down'}"
    if unity_worker_health_url:
      res = _get_url_json(unity_worker_health_url)
      status["unityWorker"] = f"Unity Worker: {'healthy' if res['ok'] else 'down'}"

  if include_n8n:
    n8n_status_url = _effective_setting("n8nStatusUrl", "N8N_STATUS_URL", "")
    if n8n_status_url:
      res = _get_url_json(n8n_status_url)
      status.setdefault("n8n", {})
      status["n8n"]["lastResult"] = "success" if res["ok"] else "failed"
      status["n8n"]["lastTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")

  snapshot = _runtime_snapshot(status)
  return {"ok": True, "snapshot": snapshot, "storeBackend": snapshot.get("storeBackend", "file")}


@app.get("/api/pipeline-state")
def pipeline_state(include_services: bool = Query(default=True), include_n8n: bool = Query(default=False)) -> Dict[str, Any]:
  status = _read_json(STATUS_FILE, {})
  queue_items = _read_json(QUEUE_FILE, [])

  if include_services:
    cloud_run_health_url = _effective_setting("cloudRunHealthUrl", "CLOUD_RUN_HEALTH_URL", "")
    unity_worker_health_url = _effective_setting("unityWorkerHealthUrl", "UNITY_WORKER_HEALTH_URL", "")
    if cloud_run_health_url:
      res = _get_url_json(cloud_run_health_url)
      status["cloudRun"] = f"Cloud Run: {'healthy' if res['ok'] else 'down'}"
    if unity_worker_health_url:
      res = _get_url_json(unity_worker_health_url)
      status["unityWorker"] = f"Unity Worker: {'healthy' if res['ok'] else 'down'}"

  if include_n8n:
    n8n_status_url = _effective_setting("n8nStatusUrl", "N8N_STATUS_URL", "")
    if n8n_status_url:
      res = _get_url_json(n8n_status_url)
      status.setdefault("n8n", {})
      status["n8n"]["lastResult"] = "success" if res["ok"] else "failed"
      status["n8n"]["lastTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")

  return {"ok": True, "pipeline": _pipeline_state(status, queue_items), "storeBackend": _STORE.backend}
