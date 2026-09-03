# 管理 OpenAPI 鉴权

## 换票

组织管理员在“开发者管理”创建凭据并授予最小 scope。客户端调用：

```http
POST /openapi/v1/developer/token
Content-Type: application/json

{"clientId":"cici-dev-...","clientSecret":"cici_cs_..."}
```

响应 `data` 包含 `accessToken`、`tokenType=Bearer`、`expiresIn` 和 `scopes`。后续管理请求使用 `Authorization: Bearer <accessToken>`。Token 默认有效 600 秒；脚本只在进程内缓存。

## Scope

| 模块 | 读取 | 创建/编辑 | 删除 |
|---|---|---|---|
| 智能体 | `agent.read` | `agent.write` | `agent.delete` |
| 技能 | `skill.read` | `skill.write` | `skill.delete` |
| MCP 服务 | `mcp.read` | `mcp.write` | `mcp.delete` |

## 错误语义

- `400`：请求字段或业务规则无效。
- `401`：开发者密钥、Token、组织或凭据责任人成员已失效。
- `403`：当前凭据缺少所需 scope。
- `404`：资源不存在或不属于当前组织。
- `409`：资源状态冲突或删除条件不满足。

管理 OpenAPI 不调用 `/auth/password/login`，不使用 Keycloak，不接受 Agent API Key。
