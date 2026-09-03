# MCP 工具模块

## 设计理解

MCP 服务是 AgentCiCi 连接外部工具能力的服务配置。一个服务可暴露多个工具，平台通过传输地址发现并调用它们；技能中的 `toolWhitelist` 再限制哪些工具可以进入智能体运行时。

- 优先使用远程 `streamableHttp` 传输和 HTTPS URL。
- `name`、`description` 应说明业务系统和能力范围，不用模糊的“工具一”。
- `headers` 可能含敏感值，只有用户明确提供时才写入，不在回答中回显。
- `timeoutSeconds` 应按外部服务延迟设置；默认 60 秒。
- `enabled=false` 会停止该服务进入运行时工具集合。
- `clientSecret` 只在创建或轮换时发送；响应只返回 `clientSecretConfigured`。
- CRUD 不包含工具发现、健康检查和实际工具调用。

## 管理 API

| 操作 | 方法与路径 | scope |
|---|---|---|
| 列表 | `GET /openapi/v1/management/mcp-servers` | `mcp.read` |
| 详情 | `GET /openapi/v1/management/mcp-servers/{serverId}` | `mcp.read` |
| 创建 | `POST /openapi/v1/management/mcp-servers` | `mcp.write` |
| 完整编辑 | `PUT /openapi/v1/management/mcp-servers/{serverId}` | `mcp.write` |
| 删除 | `DELETE /openapi/v1/management/mcp-servers/{serverId}` | `mcp.delete` |

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
