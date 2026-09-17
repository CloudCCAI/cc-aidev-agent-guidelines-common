#!/usr/bin/env python3
"""AgentCiCi platform management CLI with automatic developer-token exchange."""

from __future__ import annotations

import argparse
import io
import zipfile
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, values=None) -> None:
        from agentcici_auth import credentials, NAMES
        values = credentials() if values is None else values
        self.base_url = values[NAMES[0]].rstrip("/")
        self.client_id = values[NAMES[1]]
        self.client_secret = values[NAMES[2]]
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

    def download(self, method, path, body=None):
        headers = {"Authorization": "Bearer " + self.exchange(), "Accept": "application/zip"}
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.build_opener(NoCredentialRedirect()).open(request, timeout=180) as response:
                result = response.read(100 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"原生包导出失败 HTTP {error.code}；检查服务端部署、读取权限及资源发布状态") from None
        except urllib.error.URLError:
            raise RuntimeError("原生包导出连接失败") from None
        if len(result) > 100 * 1024 * 1024 or not zipfile.is_zipfile(io.BytesIO(result)):
            raise RuntimeError("服务端未返回有效 ZIP 或包超过 100 MiB")
        return result

    def _request(self, method: str, path: str, body: dict[str, Any] | None, authenticated: bool) -> Any:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = "Bearer " + self.exchange()
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.build_opener(NoCredentialRedirect()).open(request, timeout=30) as response:
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
    inputs = command.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--json", dest="json_value")
    inputs.add_argument("--file")


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
    if module.prog.endswith(("agents", "skills")):
        export = commands.add_parser("export", help="下载原生包到本地，不覆盖已有文件")
        export.add_argument(id_name)
        export.add_argument("--output", required=True)
        if module.prog.endswith("skills"):
            export.add_argument("--allow-draft", action="store_true")
        compile_command = commands.add_parser("compile", help="编译当前草稿")
        compile_command.add_argument(id_name)
        publish = commands.add_parser("publish", help="发布技能或指定智能体版本")
        publish.add_argument(id_name)
        if module.prog.endswith("agents"):
            publish.add_argument("--version-no", type=int, required=True)
        else:
            publish.add_argument("--change-log", default="")
    if module.prog.endswith("agents"):
        bindings = commands.add_parser("skills", help="读取技能关联")
        bindings.add_argument(id_name)
        for name in ("bind-skills", "bind-knowledge", "bind-tools"):
            binding = commands.add_parser(name, help="替换完整关联列表；空列表清空")
            binding.add_argument(id_name)
            add_payload_arguments(binding)


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


SKILL_FIELDS = "skillCode name description enabled promptFragment draftSpecText toolWhitelist kbWhitelist handoffRule outputContract runtimeApis riskLevel changeLog".split()


def execute(client, args):
    base = resource_path(args.module)
    path = base + "/" + urllib.parse.quote(getattr(args, "resource_id", ""), safe="")
    if args.command == "list":
        return client.request("GET", base)
    if args.command == "get":
        return client.request("GET", path)
    if args.command == "create":
        return client.request("POST", base, read_payload(args))
    if args.command == "update":
        body = read_payload(args)
        if args.module == "skills":
            current = client.request("GET", path)
            body = {**{k: v for k, v in current.items() if k in SKILL_FIELDS}, **body}
        return client.request("PATCH" if args.module == "agents" else "PUT", path, body)
    if args.command == "export":
        output = pathlib.Path(args.output).expanduser().resolve()
        if output.exists():
            raise RuntimeError("输出文件已存在，请选择新路径")
        if not output.parent.is_dir():
            raise RuntimeError("输出目录不存在，请先创建")
        body = {"allowDraft": args.allow_draft} if args.module == "skills" else None
        data = client.download("POST" if args.module == "skills" else "GET", path + "/package", body)
        with output.open("xb") as file:
            file.write(data)
        return {"file": str(output), "sizeBytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if args.command == "compile":
        return client.request("POST", path + "/compile", {})
    if args.command == "publish":
        if args.module == "agents":
            if args.version_no <= 0:
                raise RuntimeError("--version-no 必须是正整数")
            body = {"versionNo": args.version_no}
        else:
            body = {"changeLog": args.change_log}
        return client.request("POST", path + "/publish", body)
    if args.command == "skills":
        return client.request("GET", path + "/skills")
    if args.command.startswith("bind-"):
        field = {"bind-skills": "bindings", "bind-knowledge": "knowledgeBaseIds", "bind-tools": "toolIds"}[args.command]
        body = read_payload(args)
        if set(body) != {field} or not isinstance(body[field], list):
            raise RuntimeError("请求必须仅包含列表字段 " + field)
        return client.request("PUT" if field == "bindings" else "PATCH",
                              path + ("/skills" if field == "bindings" else ""), body)
    if args.resource_id != args.confirm_id:
        raise RuntimeError("--confirm-id 必须与待删除资源 ID 完全一致")
    return client.request("DELETE", path)


def main() -> int:
    args = parser().parse_args()
    try:
        result = execute(Client(), args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
