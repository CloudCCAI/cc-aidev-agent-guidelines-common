# 智能体模块

## 设计理解

智能体是可运行的业务角色，组合模型、系统提示词、自然语言流程 Spec、知识库、工具、技能、渠道和安全/转人工策略。设计时先明确目标用户、触发请求、必要数据与工具、输出契约、风险动作和人工确认点。

- `agentId` 是稳定技术标识，创建后不可修改；`name` 是用户可见名称。
- `summary`、`greeting` 描述用途和开场；`systemPrompt`、`specText` 决定行为与流程。
- `knowledgeBaseIds`、`toolIds`、`channels` 只在用户明确要求且对应资源已存在时绑定。
- `BALANCED`/`STRICT` 与 `COPILOT`/`AUTO` 会影响执行策略；高风险场景应优先人工确认。
- 管理 API 编辑的是定义草稿，不等于发布新版本。

## 管理 API

| 操作 | 方法与路径 | scope |
|---|---|---|
| 列表 | `GET /openapi/v1/management/agents` | `agent.read` |
| 详情 | `GET /openapi/v1/management/agents/{agentId}` | `agent.read` |
| 创建 | `POST /openapi/v1/management/agents` | `agent.write` |
| 部分编辑 | `PATCH /openapi/v1/management/agents/{agentId}` | `agent.write` |
| 软删除 | `DELETE /openapi/v1/management/agents/{agentId}` | `agent.delete` |

创建至少需要 `agentId`、`name`、`model`。编辑只发送要改变的字段；绑定字段传空数组表示清空。删除前确认 `builtin=false`，历史版本、运行和审计证据仍会保留。

```json
{
  "agentId": "support-agent",
  "name": "售后智能体",
  "model": "qwen3.7-plus",
  "summary": "回答售后问题，复杂事项转人工",
  "safetyLevel": "STRICT",
  "executionMode": "COPILOT"
}
```
