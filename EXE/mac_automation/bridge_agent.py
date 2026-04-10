#!/usr/bin/env python3
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _base_url() -> str:
    return (
        _env("BRIDGE_CLOUD_RUN_URL")
        or _env("BRIDGE_BASE_URL")
        or _env("CLOUD_RUN_URL")
        or _env("REMOTE_MCP_GATEWAY_URL")
    )


def _bridge_token() -> str:
    return (
        _env("BRIDGE_SHARED_TOKEN")
        or _env("BRIDGE_AUTH_TOKEN")
        or _env("REMOTE_API_BEARER_TOKEN")
    )


def _device_id() -> str:
    return _env("BRIDGE_DEVICE_ID", "mac-main")


def _repo_dir() -> str:
    explicit = _env("REPO_DIR")
    if explicit:
        return explicit
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _post_json(url: str, payload: Dict[str, Any], token: str = "") -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url=url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data) if data else {}


def _get_json(url: str, token: str = "") -> Dict[str, Any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url=url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data) if data else {}


def _run_shell(command: str, repo_dir: str) -> Dict[str, Any]:
    proc = subprocess.run(
        ["bash", "-lc", command],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
    }


def _execute_command(command: str, repo_dir: str) -> Dict[str, Any]:
    normalized = command.strip()
    if not normalized:
        return {"ok": False, "message": "empty command"}

    if normalized == "onepush" or normalized.startswith("onepush "):
        msg = normalized[len("onepush") :].strip()
        escaped = msg.replace('"', '\\"')
        if msg:
            shell_cmd = f'bash "{repo_dir}/EXE/one_command_git_flow.sh" "{escaped}"'
        else:
            shell_cmd = f'bash "{repo_dir}/EXE/one_command_git_flow.sh"'
        out = _run_shell(shell_cmd, repo_dir)
        return {"ok": out["returncode"] == 0, "mode": "onepush", "result": out}

    if normalized == "graph-green":
        shell_cmd = f'bash "{repo_dir}/EXE/run_reportmanager_graph_green.sh"'
        out = _run_shell(shell_cmd, repo_dir)
        return {"ok": out["returncode"] == 0, "mode": "graph-green", "result": out}

    out = _run_shell(normalized, repo_dir)
    return {"ok": out["returncode"] == 0, "mode": "shell", "result": out}


def _resolve_repo_dir(command_item: Dict[str, Any], default_repo_dir: str) -> str:
    metadata = command_item.get("metadata") or {}
    candidate = metadata.get("repo_dir", "")
    if candidate and os.path.isdir(candidate):
        return candidate
    return default_repo_dir


def _resolve_timeout_sec(command_item: Dict[str, Any]) -> int:
    metadata = command_item.get("metadata") or {}
    raw = metadata.get("timeout_sec", 300)
    try:
        value = int(raw)
    except Exception:
        value = 300
    if value < 1:
        return 1
    if value > 1800:
        return 1800
    return value


def main() -> None:
    base = _base_url().rstrip("/")
    token = _bridge_token()
    device_id = _device_id()
    repo_dir = _repo_dir()
    poll_sec = int(_env("BRIDGE_POLL_SECONDS", "5") or "5")

    if not base:
        raise SystemExit("BRIDGE_CLOUD_RUN_URL or CLOUD_RUN_URL is required")

    if not os.path.isdir(repo_dir):
        raise SystemExit(f"repo_dir not found: {repo_dir}")

    while True:
        try:
            claim = _post_json(
                f"{base}/v1/bridge/commands/claim",
                {"agent_id": device_id},
                token=token,
            )
            msg = claim.get("command") or {}
            command_id = msg.get("command_id", "")
            if not command_id:
                time.sleep(poll_sec)
                continue

            command_text = msg.get("command") or msg.get("command_text", "")
            command_repo_dir = _resolve_repo_dir(msg, default_repo_dir=repo_dir)
            timeout_sec = _resolve_timeout_sec(msg)
            started = time.time()
            result = _execute_command(command_text, repo_dir=command_repo_dir)
            elapsed_ms = int((time.time() - started) * 1000)

            success = bool(result.get("ok"))
            run_result = result.get("result") or {}
            exit_code = int(run_result.get("returncode", 1))
            if elapsed_ms > timeout_sec * 1000:
                success = False
                exit_code = 124
                run_result["stderr"] = (run_result.get("stderr", "") + "\n[bridge-agent] timeout exceeded").strip()

            _post_json(
                f"{base}/v1/bridge/commands/result",
                {
                    "command_id": command_id,
                    "agent_id": device_id,
                    "success": success,
                    "exit_code": exit_code,
                    "stdout": run_result.get("stdout", ""),
                    "stderr": run_result.get("stderr", ""),
                    "metadata": {
                        "mode": result.get("mode", ""),
                        "elapsed_ms": elapsed_ms,
                        "repo_dir": command_repo_dir,
                    },
                },
                token=token,
            )
        except urllib.error.HTTPError as e:
            # 서버 오류/인증 오류 시 잠깐 대기 후 재시도
            print(f"[bridge-agent] http error: {e.code}", flush=True)
            time.sleep(max(3, poll_sec))
        except Exception as e:
            print(f"[bridge-agent] error: {e}", flush=True)
            time.sleep(max(3, poll_sec))


if __name__ == "__main__":
    main()
