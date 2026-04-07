#!/usr/bin/env python3
import json
import os
from datetime import datetime
from typing import Any, Dict, List
from urllib import error, request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
STATIC_DIR = os.path.join(ROOT, "static")

SESSIONS_FILE = os.path.join(DATA_DIR, "chat_sessions.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")


def _read_json(path: str, default: Any) -> Any:
  if not os.path.isfile(path):
    return default
  with open(path, encoding="utf-8") as f:
    return json.load(f)


def _write_json(path: str, data: Any) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


def _get_url_json(url: str, timeout: int = 10) -> Dict[str, Any]:
  try:
    with request.urlopen(url, timeout=timeout) as resp:
      body = resp.read().decode("utf-8", errors="ignore")
      return {"ok": True, "status": resp.status, "body": body}
  except error.HTTPError as e:
    return {"ok": False, "status": e.code, "body": ""}
  except Exception:
    return {"ok": False, "status": 0, "body": ""}


app = FastAPI(title="remote-dev-web-browser")
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class MessageIn(BaseModel):
  sessionId: str
  role: str
  text: str


@app.get("/")
def index():
  return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/chat/sessions")
def get_sessions() -> List[Dict[str, Any]]:
  return _read_json(SESSIONS_FILE, [])


@app.get("/api/chat/messages")
def get_messages() -> List[Dict[str, Any]]:
  return _read_json(MESSAGES_FILE, [])


@app.post("/api/chat/messages")
def add_message(message: MessageIn) -> Dict[str, Any]:
  messages = _read_json(MESSAGES_FILE, [])
  messages.append(message.model_dump())
  _write_json(MESSAGES_FILE, messages)

  sessions = _read_json(SESSIONS_FILE, [])
  for s in sessions:
    if s.get("id") == message.sessionId:
      s["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
  _write_json(SESSIONS_FILE, sessions)
  return {"ok": True}


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
  status = _read_json(STATUS_FILE, {})

  cloud_run_health_url = os.environ.get("CLOUD_RUN_HEALTH_URL", "")
  unity_worker_health_url = os.environ.get("UNITY_WORKER_HEALTH_URL", "")
  if cloud_run_health_url:
    res = _get_url_json(cloud_run_health_url)
    status["cloudRun"] = f"Cloud Run: {'healthy' if res['ok'] else 'down'}"
  if unity_worker_health_url:
    res = _get_url_json(unity_worker_health_url)
    status["unityWorker"] = f"Unity Worker: {'healthy' if res['ok'] else 'down'}"

  n8n_status_url = os.environ.get("N8N_STATUS_URL", "")
  if n8n_status_url:
    res = _get_url_json(n8n_status_url)
    status.setdefault("n8n", {})
    status["n8n"]["lastResult"] = "success" if res["ok"] else "failed"
    status["n8n"]["lastTime"] = datetime.now().strftime("%Y-%m-%d %H:%M")

  if not status:
    raise HTTPException(status_code=500, detail="status data not found")
  return status
