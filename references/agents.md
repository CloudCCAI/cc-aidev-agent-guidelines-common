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

## 关联资源与编译发布

新增接口需要部署包含本次扩展的后端；404 时停止并报告，不以管理后台接口替代。开发者凭据限定 org，新接口还检查凭据绑定成员的智能体权限。

| 操作 | 方法与路径 | scope / 智能体权限 |
|---|---|---|
| 查询技能关联 | `GET /openapi/v1/management/agents/{agentId}/skills` | agent.read / VIEW |
| 替换技能关联 | `PUT /openapi/v1/management/agents/{agentId}/skills` | agent.write / EDIT |
| 编译当前草稿 | `POST /openapi/v1/management/agents/{agentId}/compile` | agent.write / EDIT |
| 发布指定版本 | `POST /openapi/v1/management/agents/{agentId}/publish` | agent.write / PUBLISH |

技能关联请求为 `{"bindings":[{"skillId":123,"activationMode":"always-on","priority":10,"enabled":true}]}`。也可使用已有 skillCode。先查询完整列表，再加入或移除目标；提交空列表清空可手动管理的关联，系统内部关联遵循服务端保留规则。技能、知识库和工具必须来自当前 org 可使用资源，不复制其他 org 的 ID。

知识库和工具通过现有 PATCH 接口关联，以下命令仅改变对应字段。三种 bind 命令均替换完整列表，操作前先读取现状保留其他关联。

```bash
python3 scripts/agentcici_manage.py agents skills AGENT_ID
python3 scripts/agentcici_manage.py agents bind-skills AGENT_ID --file /absolute/path/bindings.json
python3 scripts/agentcici_manage.py agents bind-knowledge AGENT_ID --json '{"knowledgeBaseIds":[123]}'
python3 scripts/agentcici_manage.py agents bind-tools AGENT_ID --json '{"toolIds":["query_customer"]}'
python3 scripts/agentcici_manage.py agents compile AGENT_ID
python3 scripts/agentcici_manage.py agents publish AGENT_ID --version-no 1
python3 scripts/agentcici_manage.py agents delete AGENT_ID --confirm-id AGENT_ID
```

发布 version-no 必须来自本次编译返回的 draftVersionNo，不固定写 1。编译会保存新草稿版本；先检查编译结果，再发布该版本，后端执行现有发布校验。通用发布不添加 API 渠道；开启运行 OpenAPI 参考运行接口文档。

生日邮件示例顺序：创建/编辑邮件技能 → 编译并发布技能 → 创建/编辑智能体 → 关联技能、知识库、工具 → 编译智能体 → 发布返回的版本。定义编辑和关联修改只有重新编译发布后才进入新的运行版本。
