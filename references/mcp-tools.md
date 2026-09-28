# MCP 工具模块

## 设计理解

MCP 服务是 AgentCiCi 连接外部工具能力的服务配置。一个服务可暴露多个工具，平台通过传输地址发现并调用它们；技能中的 `toolWhitelist` 再限制哪些工具可以进入智能体运行时。

- 优先使用远程 `streamableHttp` 传输和 HTTPS URL。
- `name`、`description` 应说明业务系统和能力范围，不用模糊的“工具一”。
- `headers` 可能含敏感值，只有用户明确提供时才写入，不在回答中回显。
- `timeoutSeconds` 应按外部服务延迟设置；默认 60 秒。
- `enabled=false` 会停止该服务进入运行时工具集合。
- `clientSecret` 只在创建或轮换时发送；响应只返回 `clientSecretConfigured`。
- `discover` 会连接 MCP 服务并刷新工具缓存；`tools` 只读取缓存。工具由 MCP 服务提供，不能在平台单独创建或编辑；本技能不调用工具，也不执行健康检查。

## 管理 API

| 操作 | 方法与路径 | scope |
|---|---|---|
| 列表 | `GET /openapi/v1/management/mcp-servers` | `mcp.read` |
| 详情 | `GET /openapi/v1/management/mcp-servers/{serverId}` | `mcp.read` |
| 创建 | `POST /openapi/v1/management/mcp-servers` | `mcp.write` |
| 完整编辑 | `PUT /openapi/v1/management/mcp-servers/{serverId}` | `mcp.write` |
| 删除 | `DELETE /openapi/v1/management/mcp-servers/{serverId}` | `mcp.delete` |
| 发现并刷新工具 | `POST /openapi/v1/management/mcp-servers/{serverId}/discover` | `mcp.write` |
| 读取已发现工具 | `GET /openapi/v1/management/mcp-servers/{serverId}/tools` | `mcp.read` |

创建与编辑至少需要 `name`、`transportType`、`url`。`PUT` 前先读取现状并提交完整对象；需要保留已配置的 Client Secret 时不传或传空 `clientSecret`。

```json
{
  "name": "订单工具服务",
  "description": "提供订单查询工具",
  "transportType": "streamableHttp",
  "url": "https://tools.example.com/mcp",
  "headers": "{}",
  "timeoutSeconds": 60,
  "enabled": true,
  "authType": "NONE"
}
```

## 从 MCP 到智能体

1. 用 `mcp list|get|create|update` 查找或配置服务；编辑时命令先读取现状并保留未修改字段。
2. `tools list` 读取组织现有的内置、自定义与应用 MCP 工具，需 `agent.read` 权限；普通 MCP 服务的工具用 `mcp tools SERVER_ID` 读取，需 `mcp.read` 权限。需要刷新时先运行 `mcp discover SERVER_ID`，需 `mcp.write` 权限。发现结果包含每个工具的 `name`、描述和输入结构。发现失败或缓存状态不是 `ready` 时，不把旧缓存当作已验证的当前工具。
3. 读取目标智能体详情，保留现有 `toolIds`，只加入用户选中的现有工具名称，运行 `agents bind-tools AGENT_ID --file /absolute/path/binding.json`。请求体是完整 `{"toolIds":["existing_tool","selected_tool"]}`；此命令替换全部工具关联。
4. 如需生效到已发布智能体，按 [智能体编译发布](agents.md#关联资源与编译发布) 编译并发布本次返回的版本。技能的 `toolWhitelist` 如有限制，也要包含选中的工具。
