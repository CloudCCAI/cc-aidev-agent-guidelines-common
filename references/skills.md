# 技能模块

## 设计理解

技能是可复用的行为与流程资产，用于把提示片段、自然语言 Spec、工具/知识白名单、运行 API、输出契约和风险规则组合起来，再绑定给一个或多个智能体。

- `skillCode` 是稳定技术标识；名称和描述帮助用户及 AI 判断何时使用。
- `draftSpecText` 描述目标、触发、步骤和边界；`promptFragment` 是进入运行提示词的直接行为规则。
- `toolWhitelist`、`kbWhitelist` 应保持最小集合。
- `handoffRule` 明确转人工条件；`outputContract` 明确可验证输出；`riskLevel` 使用 `LOW`、`MEDIUM` 或 `HIGH`。
- 平台标准技能可读取，但通常不可编辑或删除；管理 API 创建的都是租户自定义技能。
- CRUD 只管理草稿定义，不包含发布、回滚、导入导出和智能编写。

## 管理 API

| 操作 | 方法与路径 | scope |
|---|---|---|
| 列表 | `GET /openapi/v1/management/skills` | `skill.read` |
| 详情 | `GET /openapi/v1/management/skills/{skillId}` | `skill.read` |
| 创建 | `POST /openapi/v1/management/skills` | `skill.write` |
| 完整编辑 | `PUT /openapi/v1/management/skills/{skillId}` | `skill.write` |
| 删除 | `DELETE /openapi/v1/management/skills/{skillId}` | `skill.delete` |

创建与编辑至少需要 `skillCode` 和 `name`。`PUT` 必须先读取现状，再提交合并后的完整对象。技能仍被智能体绑定或被已发布运行时引用时不能删除；删除请求可带 `{"reason":"..."}`。

```json
{
  "skillCode": "order-status-guide",
  "name": "订单状态说明",
  "description": "查询并解释订单状态",
  "enabled": true,
  "draftSpecText": "先确认订单号，再查询订单；涉及退款时转人工。",
  "promptFragment": "只基于订单查询结果回答，不得猜测。",
  "toolWhitelist": ["query_order"],
  "kbWhitelist": [],
  "handoffRule": "退款、改价或查询失败时转人工",
  "outputContract": "输出状态、依据和下一步动作",
  "runtimeApis": [],
  "riskLevel": "MEDIUM"
}
```
