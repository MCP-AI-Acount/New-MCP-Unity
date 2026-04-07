"""
Unity 다중 프로젝트 레지스트리 관리
"""

import json
import os
from typing import Any, Dict


def _registry_path() -> str:
    return os.environ.get("UNITY_PROJECT_REGISTRY_PATH", "/tmp/unity-project-registry.json")


def load_registry() -> Dict[str, Any]:
    path = _registry_path()
    if not os.path.isfile(path):
        return {"active_project": "", "projects": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_registry(data: Dict[str, Any]) -> Dict[str, Any]:
    path = _registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def set_project(project_name: str, project_path: str, set_active: bool = True) -> Dict[str, Any]:
    data = load_registry()
    data.setdefault("projects", {})
    data["projects"][project_name] = project_path
    if set_active:
        data["active_project"] = project_name
    return save_registry(data)


def resolve_project_path(project_name: str = "", project_path: str = "") -> str:
    if project_path:
        return project_path
    data = load_registry()
    projects = data.get("projects", {})
    if project_name:
        return projects.get(project_name, "")
    active_name = data.get("active_project", "")
    if active_name:
        return projects.get(active_name, "")
    return ""
