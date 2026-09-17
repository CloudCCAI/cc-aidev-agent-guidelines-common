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

## AI 应用申请

提交 ZIP 需要 application.submit；查询、下载本组织申请需要 application.read。已有凭据不会自动新增权限，组织管理员可在开发者管理中编辑权限。目标环境需已部署申请接收接口；这两个 scope 不授予平台审核、发布或跨组织访问权限。OSS 凭据只由后端配置，不使用 org 开发者凭据作为 OSS 密钥。

## Base64 登录与持久化（1.1.0）

运行 `python3 scripts/agentcici_auth.py login`，粘贴后台复制的 Base64 文本，交互输入不回显；自动化调用可通过标准输入提供，禁止将原文写入临时文件、命令参数或日志。输入被严格解析为 AGENTCICI_BASE_URL、AGENTCICI_CLIENT_ID、AGENTCICI_CLIENT_SECRET 三条 export，支持 UTF-8 与 shell 引号，但不执行解码内容。只接受 HTTPS origin 或 localhost/127.0.0.1/::1 的 HTTP 开发地址，拒绝重定向换票。

登录成功后 Secret 存在 macOS 登录钥匙串（服务名 AgentCiCi Developer Login）；普通配置 `~/.config/agentcici/login.json` 权限 600，只包含地址、Client ID、随机钥匙串账号。新登录验证失败不覆盖旧登录。一个本地用户默认保存一个当前身份，切换组织使用该组织的新登录信息。不得根据 Client ID 猜测组织。

status 不读取或显示 Secret，只报告保存状态。logout 删除钥匙串项和配置，不撤销远程凭据；如果仍设置三项环境变量，命令仍会使用环境变量。钥匙串被锁定/授权拒绝时明确报错，不回退到明文文件。服务端停用/轮换密钥后，重新复制并 login；应用命令发起远程写入失败后不要自动重试以掩盖鉴权错误。

管理命令与应用 submit/status 共享此登录读取逻辑；本地 package/validate 不需要登录。Base64 是编码，不改变这些数据作为凭据的处理方式。
