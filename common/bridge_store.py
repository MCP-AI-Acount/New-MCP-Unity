"""
Cloud bridge store (Firestore with in-memory fallback).
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _MemoryBridgeStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._messages: List[Dict[str, Any]] = []
        self._commands: Dict[str, Dict[str, Any]] = {}

    def create_message(
        self,
        session_id: str,
        role: str,
        text: str,
        device: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        msg = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": role,
            "text": text,
            "device": device,
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
        with self._lock:
            self._messages.append(msg)
        return msg

    def list_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            matches = [m for m in self._messages if m.get("session_id") == session_id]
        matches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return list(reversed(matches[:limit]))

    def create_command(
        self,
        session_id: str,
        command_text: str,
        target: str,
        requested_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        command_id = str(uuid.uuid4())
        now = _now_iso()
        cmd = {
            "command_id": command_id,
            "session_id": session_id,
            "target": target,
            "command_text": command_text,
            "requested_by": requested_by,
            "metadata": metadata or {},
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "picked_by": "",
            "picked_at": "",
            "completed_at": "",
            "exit_code": None,
            "output": "",
            "error": "",
        }
        with self._lock:
            self._commands[command_id] = cmd
        return cmd

    def poll_command(self, target: str, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            queued = [
                c for c in self._commands.values() if c.get("target") == target and c.get("status") == "queued"
            ]
            queued.sort(key=lambda x: x.get("created_at", ""))
            if not queued:
                return None
            cmd = queued[0]
            cmd["status"] = "running"
            cmd["picked_by"] = agent_id
            cmd["picked_at"] = _now_iso()
            cmd["updated_at"] = cmd["picked_at"]
            return dict(cmd)

    def complete_command(
        self,
        command_id: str,
        exit_code: int,
        output: str = "",
        error: str = "",
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            cmd = self._commands.get(command_id)
            if not cmd:
                return None
            cmd["exit_code"] = int(exit_code)
            cmd["output"] = output
            cmd["error"] = error
            cmd["status"] = "completed" if int(exit_code) == 0 else "failed"
            cmd["completed_at"] = _now_iso()
            cmd["updated_at"] = cmd["completed_at"]
            return dict(cmd)

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cmd = self._commands.get(command_id)
            return dict(cmd) if cmd else None

    def list_commands(self, target: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._commands.values())
        if target:
            items = [x for x in items if x.get("target") == target]
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items[: max(1, min(limit, 200))]


class BridgeStore:
    def __init__(self) -> None:
        self._memory = _MemoryBridgeStore()
        self._commands_collection = "bridge_commands"
        self._messages_collection = "bridge_messages"
        self._firestore_client = None
        self._firestore = None

        mode = (self._env("BRIDGE_STORE_MODE", "auto") or "auto").lower()
        if mode == "memory":
            return

        try:
            from google.cloud import firestore  # type: ignore

            project_id = self._env("GOOGLE_CLOUD_PROJECT", "") or self._env("PROJECT_ID", "")
            self._firestore_client = firestore.Client(project=project_id or None)
            self._firestore = firestore
            self._commands_collection = self._env("BRIDGE_COMMANDS_COLLECTION", "bridge_commands")
            self._messages_collection = self._env("BRIDGE_MESSAGES_COLLECTION", "bridge_messages")
        except Exception:
            self._firestore_client = None
            self._firestore = None

    @staticmethod
    def _env(key: str, default: str) -> str:
        import os

        return os.environ.get(key, default)

    def _use_firestore(self) -> bool:
        return self._firestore_client is not None and self._firestore is not None

    def create_message(
        self,
        session_id: str,
        role: str,
        text: str,
        device: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._use_firestore():
            return self._memory.create_message(session_id, role, text, device=device, metadata=metadata)

        message_id = str(uuid.uuid4())
        doc = {
            "message_id": message_id,
            "session_id": session_id,
            "role": role,
            "text": text,
            "device": device,
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
        self._firestore_client.collection(self._messages_collection).document(message_id).set(doc)
        return doc

    def list_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if not self._use_firestore():
            return self._memory.list_messages(session_id, limit=limit)

        query = (
            self._firestore_client.collection(self._messages_collection)
            .where("session_id", "==", session_id)
            .order_by("created_at", direction=self._firestore.Query.DESCENDING)
            .limit(max(1, min(limit, 200)))
        )
        items = [doc.to_dict() for doc in query.stream()]
        return list(reversed(items))

    def create_command(
        self,
        session_id: str,
        command_text: str,
        target: str,
        requested_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._use_firestore():
            return self._memory.create_command(
                session_id=session_id,
                command_text=command_text,
                target=target,
                requested_by=requested_by,
                metadata=metadata,
            )

        command_id = str(uuid.uuid4())
        now = _now_iso()
        doc = {
            "command_id": command_id,
            "session_id": session_id,
            "target": target,
            "command_text": command_text,
            "requested_by": requested_by,
            "metadata": metadata or {},
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "picked_by": "",
            "picked_at": "",
            "completed_at": "",
            "exit_code": None,
            "output": "",
            "error": "",
        }
        self._firestore_client.collection(self._commands_collection).document(command_id).set(doc)
        return doc

    def poll_command(self, target: str, agent_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_firestore():
            return self._memory.poll_command(target=target, agent_id=agent_id)

        candidates = (
            self._firestore_client.collection(self._commands_collection)
            .where("target", "==", target)
            .where("status", "==", "queued")
            .order_by("created_at", direction=self._firestore.Query.ASCENDING)
            .limit(5)
            .stream()
        )

        for snapshot in candidates:
            ref = snapshot.reference
            transaction = self._firestore_client.transaction()

            @self._firestore.transactional
            def claim(txn, doc_ref):
                fresh = doc_ref.get(transaction=txn)
                if not fresh.exists:
                    return None
                data = fresh.to_dict() or {}
                if data.get("status") != "queued":
                    return None
                now = _now_iso()
                txn.update(
                    doc_ref,
                    {
                        "status": "running",
                        "picked_by": agent_id,
                        "picked_at": now,
                        "updated_at": now,
                    },
                )
                data["status"] = "running"
                data["picked_by"] = agent_id
                data["picked_at"] = now
                data["updated_at"] = now
                return data

            claimed = claim(transaction, ref)
            if claimed:
                return claimed

        return None

    def complete_command(
        self,
        command_id: str,
        exit_code: int,
        output: str = "",
        error: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not self._use_firestore():
            return self._memory.complete_command(command_id, exit_code=exit_code, output=output, error=error)

        ref = self._firestore_client.collection(self._commands_collection).document(command_id)
        snap = ref.get()
        if not snap.exists:
            return None

        status = "completed" if int(exit_code) == 0 else "failed"
        now = _now_iso()
        ref.update(
            {
                "status": status,
                "exit_code": int(exit_code),
                "output": output,
                "error": error,
                "completed_at": now,
                "updated_at": now,
            }
        )
        data = snap.to_dict() or {}
        data.update(
            {
                "status": status,
                "exit_code": int(exit_code),
                "output": output,
                "error": error,
                "completed_at": now,
                "updated_at": now,
            }
        )
        return data

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_firestore():
            return self._memory.get_command(command_id)

        snap = self._firestore_client.collection(self._commands_collection).document(command_id).get()
        if not snap.exists:
            return None
        return snap.to_dict()

    def list_commands(self, target: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        if not self._use_firestore():
            return self._memory.list_commands(target=target, limit=limit)

        query = self._firestore_client.collection(self._commands_collection)
        if target:
            query = query.where("target", "==", target)
        query = query.order_by("created_at", direction=self._firestore.Query.DESCENDING).limit(
            max(1, min(limit, 200))
        )
        return [doc.to_dict() for doc in query.stream()]


_bridge_store = BridgeStore()


def _default_session_id() -> str:
    import os

    return os.environ.get("BRIDGE_DEFAULT_SESSION_ID", "default")


def _default_target() -> str:
    import os

    return os.environ.get("BRIDGE_DEFAULT_TARGET", "mac-main")


def push_message(
    role: str,
    text: str,
    source: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> Dict[str, Any]:
    sid = session_id or _default_session_id()
    return _bridge_store.create_message(
        session_id=sid,
        role=role,
        text=text,
        device=source,
        metadata=metadata,
    )


def list_messages(limit: int = 50, session_id: str = "") -> List[Dict[str, Any]]:
    sid = session_id or _default_session_id()
    return _bridge_store.list_messages(session_id=sid, limit=limit)


def queue_command(
    command: str,
    source: str = "",
    repo_dir: str = "",
    timeout_sec: int = 300,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: str = "",
    target: str = "",
) -> Dict[str, Any]:
    sid = session_id or _default_session_id()
    merged_metadata: Dict[str, Any] = dict(metadata or {})
    if repo_dir:
        merged_metadata["repo_dir"] = repo_dir
    merged_metadata["timeout_sec"] = int(timeout_sec)
    tgt = target or merged_metadata.get("target") or _default_target()
    item = _bridge_store.create_command(
        session_id=sid,
        command_text=command,
        target=tgt,
        requested_by=source,
        metadata=merged_metadata,
    )
    item["command"] = item.get("command_text", "")
    return item


def claim_next_pending_command(agent_id: str) -> Optional[Dict[str, Any]]:
    item = _bridge_store.poll_command(target=agent_id, agent_id=agent_id)
    if not item:
        return None
    item["command"] = item.get("command_text", "")
    return item


def save_command_result(
    command_id: str,
    agent_id: str,
    success: bool,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    _ = agent_id
    _ = success
    _ = metadata
    return _bridge_store.complete_command(
        command_id=command_id,
        exit_code=exit_code,
        output=stdout,
        error=stderr,
    )


def list_commands(limit: int = 50, target: str = "") -> List[Dict[str, Any]]:
    return _bridge_store.list_commands(target=target, limit=limit)
