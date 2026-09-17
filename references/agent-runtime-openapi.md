# 单智能体运行 OpenAPI 教程

## 与管理 OpenAPI 的区别

运行 OpenAPI 用于让外部应用与一个已发布智能体对话、维护会话和上传文件。它使用该智能体自己的 Agent API Key：`Authorization: Bearer <AGENTCICI_API_KEY>`。开发者管理 Token 不能调用运行 API，Agent API Key 也不能管理平台资产。

Agent API Key 由组织管理员在智能体详情的“开放 API 文档/密钥管理”中创建、限制来源并管理生命周期。

## 快速调用

```bash
curl -X POST "$AGENTCICI_BASE_URL/openapi/v1/chat-messages" \
  -H "Authorization: Bearer $AGENTCICI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-question-001" \
  -d '{"user":"customer-001","query":"我的订单到哪里了？","responseMode":"blocking"}'
```

- `user` 是调用方稳定用户标识。
- `query` 是本轮问题。
- `responseMode` 使用 `blocking` 获取 JSON，或 `streaming` 获取 SSE。
- 后续轮次传回 `conversationId`；有副作用的请求应设置稳定的 `Idempotency-Key`。

## 运行端点

| 能力 | 方法与路径 |
|---|---|
| 参数信息 | `GET /openapi/v1/parameters` |
| 发送消息 | `POST /openapi/v1/chat-messages` |
| 停止流式任务 | `POST /openapi/v1/chat-messages/{taskId}/stop` |
| 会话列表 | `GET /openapi/v1/conversations` |
| 消息列表 | `GET /openapi/v1/messages` |
| 会话改名 | `POST /openapi/v1/conversations/{conversationId}/name` |
| 删除会话 | `DELETE /openapi/v1/conversations/{conversationId}` |
| 消息反馈 | `POST /openapi/v1/messages/{messageId}/feedbacks` |
| 推荐问题 | `GET /openapi/v1/messages/{messageId}/suggested` |
| 上传文件 | `POST /openapi/v1/files/upload` |
| 导入远程文件 | `POST /openapi/v1/files/import` |

上传接口返回文件 `id` 后，在 `chat-messages.files[].upload_file_id` 中引用。文件类型、大小、模型能力或解析失败都应作为明确错误处理，不要静默忽略附件。

## 发布与凭据相互独立

开启 API 渠道即可满足发布入口条件，不要求先创建 Key。未发布的智能体也可创建 Key，开发者管理接口仍检查智能体存在及 OPENAPI 权限。创建 Key 不会自动发布或开启渠道；实际调用仍需要满足运行端的鉴权、发布及渠道条件。
