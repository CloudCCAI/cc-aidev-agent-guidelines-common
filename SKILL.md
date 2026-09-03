---
name: cc-aidev-agent-guidelines-common
description: 通过 AgentCiCi 自管开发者密钥自动换取短期 Token，理解并管理组织内的智能体、技能和 MCP 服务；覆盖三个模块的产品设计说明、CRUD 管理 OpenAPI，以及单智能体运行 OpenAPI 教程。当用户要求设计或实施 AgentCiCi 智能体/技能/MCP、查看或修改平台资产、接入 AgentCiCi OpenAPI 时使用。
---

# AgentCiCi 平台管理

本 Skill 同时服务两个阶段：设计阶段先理解模块职责与边界，实施阶段再调用明确的管理 API。不要在不了解现有资源的情况下直接写入。

## 前置配置

要求组织管理员先在 AgentCiCi“开发者管理”创建最小权限凭据，再由用户安全配置：

```bash
export AGENTCICI_BASE_URL="https://your-agentcici-host"
export AGENTCICI_CLIENT_ID="cici-dev-..."
export AGENTCICI_CLIENT_SECRET="cici_cs_..."
```

- 脚本自动调用 `/openapi/v1/developer/token` 换取短期 Token；不要要求用户手工提供 Token。
- 不把 Client Secret 或 Token 写入文件、日志、命令参数示例或回答。
- 缺少配置时只指出缺少的环境变量名，让用户配置后重试。
- 管理 OpenAPI 不使用 Keycloak，也不接受单智能体运行 API Key。

## 选择模块

- 智能体设计或 CRUD：先读 [references/agents.md](references/agents.md)，实施时运行 `scripts/agentcici_manage.py agents ...`。
- 调用已发布智能体：读 [references/agent-runtime-openapi.md](references/agent-runtime-openapi.md)。这套运行 API 使用 Agent API Key，不使用开发者密钥。
- 技能设计或 CRUD：先读 [references/skills.md](references/skills.md)，实施时运行 `scripts/agentcici_manage.py skills ...`。
- MCP 服务设计或 CRUD：先读 [references/mcp-tools.md](references/mcp-tools.md)，实施时运行 `scripts/agentcici_manage.py mcp ...`。
- 换票、scope、错误语义：读 [references/authentication.md](references/authentication.md)。

只读取当前任务所需的参考文件。

## 实施工作流

1. 根据意图确定模块和所需 `*.read`、`*.write`、`*.delete` scope。
2. 编辑或删除前必须先 `get` 当前资源，核对 ID、来源、是否内置以及引用约束。
3. 创建和编辑只写入用户已明确的信息；不要擅自绑定知识库、工具、渠道或凭据。
4. 技能与 MCP 编辑使用完整 `PUT`，先读取原对象，再合并用户确认的变更，最后提交完整请求体。
5. 删除前向用户确认精确目标；命令行必须把相同 ID 再传给 `--confirm-id`。
6. 输出资源 ID、关键变更和任何约束；不得回显凭据或 Token。

## 命令入口

```bash
python3 scripts/agentcici_manage.py agents list
python3 scripts/agentcici_manage.py agents get AGENT_ID
python3 scripts/agentcici_manage.py agents create --file /absolute/path/agent.json
python3 scripts/agentcici_manage.py agents update AGENT_ID --json '{"summary":"新的说明"}'

python3 scripts/agentcici_manage.py skills list
python3 scripts/agentcici_manage.py skills create --file /absolute/path/skill.json
python3 scripts/agentcici_manage.py skills update SKILL_ID --file /absolute/path/skill.json

python3 scripts/agentcici_manage.py mcp list
python3 scripts/agentcici_manage.py mcp create --file /absolute/path/mcp.json
python3 scripts/agentcici_manage.py mcp update SERVER_ID --file /absolute/path/mcp.json
```

长数据优先使用 `--file`，减少 shell 转义和敏感内容进入终端历史的风险。
