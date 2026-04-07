#!/usr/bin/env python3
import argparse
import json
from urllib import request


def post(url: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get(url: str, token: str) -> dict:
    req = request.Request(
        url=url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Unity 다중 프로젝트 관리")
    parser.add_argument("--worker-url", required=True)
    parser.add_argument("--token", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create")
    create.add_argument("--project-name", required=True)
    create.add_argument("--project-path", default="")
    create.add_argument("--set-active", action="store_true")

    active = sub.add_parser("set-active")
    active.add_argument("--project-name", required=True)
    active.add_argument("--project-path", default="")

    sub.add_parser("list")

    args = parser.parse_args()
    base = args.worker_url.rstrip("/")
    if args.cmd == "create":
        out = post(
            base + "/v1/projects/create",
            args.token,
            {
                "project_name": args.project_name,
                "project_path": args.project_path,
                "set_active": args.set_active,
            },
        )
    elif args.cmd == "set-active":
        out = post(
            base + "/v1/projects/set-active",
            args.token,
            {
                "project_name": args.project_name,
                "project_path": args.project_path,
                "set_active": True,
            },
        )
    else:
        out = get(base + "/v1/projects", args.token)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
