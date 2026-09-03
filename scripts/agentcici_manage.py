#!/usr/bin/env python3
"""AgentCiCi platform management CLI with automatic developer-token exchange."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def env(name: str, default: str = "") -> str:
    value = os.environ.get(name, default).strip()
    if not value:
        raise RuntimeError(f"缺少环境变量：{name}")
    return value


class Client:
    def __init__(self) -> None:
        self.base_url = env("AGENTCICI_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        self.client_id = env("AGENTCICI_CLIENT_ID")
        self.client_secret = env("AGENTCICI_CLIENT_SECRET")
        self.token = ""

    def exchange(self) -> str:
        if not self.token:
            result = self._request("POST", "/openapi/v1/developer/token", {
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
            }, authenticated=False)
            self.token = result["accessToken"]
        return self.token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        return self._request(method, path, body, authenticated=True)

    def _request(self, method: str, path: str, body: dict[str, Any] | None, authenticated: bool) -> Any:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.exchange()
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                message = json.loads(error.read().decode("utf-8")).get("message")
            except Exception:
                message = None
            raise RuntimeError(message or f"AgentCiCi 返回 HTTP {error.code}") from None
        except urllib.error.URLError as error:
            raise RuntimeError(f"无法连接 AgentCiCi：{error.reason}") from None
        if not envelope.get("success"):
            raise RuntimeError(envelope.get("message") or "AgentCiCi 请求失败")
        return envelope.get("data")


def read_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_value:
        value = json.loads(args.json_value)
    elif args.file:
        value = json.loads(pathlib.Path(args.file).read_text(encoding="utf-8"))
    else:
        raise RuntimeError("必须提供 --json 或 --file")
    if not isinstance(value, dict):
        raise RuntimeError("请求数据必须是 JSON 对象")
    return value


def add_payload_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--json", dest="json_value")
    command.add_argument("--file")


def add_resource_commands(module: argparse.ArgumentParser, id_name: str) -> None:
    commands = module.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="列出资源")
    get = commands.add_parser("get", help="读取资源详情")
    get.add_argument(id_name)
    create = commands.add_parser("create", help="创建资源")
    add_payload_arguments(create)
    update = commands.add_parser("update", help="更新资源")
    update.add_argument(id_name)
    add_payload_arguments(update)
    delete = commands.add_parser("delete", help="删除资源")
    delete.add_argument(id_name)
    delete.add_argument("--confirm-id", required=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="使用开发者密钥管理 AgentCiCi 智能体、技能和 MCP 服务")
    modules = root.add_subparsers(dest="module", required=True)
    add_resource_commands(modules.add_parser("agents", help="管理智能体"), "resource_id")
    add_resource_commands(modules.add_parser("skills", help="管理技能"), "resource_id")
    add_resource_commands(modules.add_parser("mcp", help="管理 MCP 服务"), "resource_id")
    return root


def resource_path(module: str) -> str:
    suffix = {"agents": "agents", "skills": "skills", "mcp": "mcp-servers"}[module]
    return "/openapi/v1/management/" + suffix


def main() -> int:
    args = parser().parse_args()
    try:
        client = Client()
        base = resource_path(args.module)
        if args.command == "list":
            result = client.request("GET", base)
        elif args.command == "get":
            result = client.request("GET", base + "/" + urllib.parse.quote(args.resource_id, safe=""))
        elif args.command == "create":
            result = client.request("POST", base, read_payload(args))
        elif args.command == "update":
            method = "PATCH" if args.module == "agents" else "PUT"
            result = client.request(method, base + "/" + urllib.parse.quote(args.resource_id, safe=""), read_payload(args))
        else:
            if args.resource_id != args.confirm_id:
                raise RuntimeError("--confirm-id 必须与待删除资源 ID 完全一致")
            result = client.request("DELETE", base + "/" + urllib.parse.quote(args.resource_id, safe=""))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
