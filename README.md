# AgentCiCi 开发与管理 Skill

`cc-aidev-agent-guidelines-common` 是面向 Codex 等 AI 开发助手的 AgentCiCi 技能包，用于：

- 管理组织内的智能体、技能和 MCP 服务。
- 编译、发布和导出 AgentCiCi 原生资源包。
- 开发纯前端 AI Web 应用，集成 CloudCC 菜单、按钮或全局入口。
- 准备、校验和提交 AI 应用发布申请包。

当前版本：`1.4.7`

## 安装

直接将仓库克隆到 Codex 技能目录：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/CloudCCAI/cc-aidev-agent-guidelines-common.git \
  ~/.codex/skills/cc-aidev-agent-guidelines-common
```

已安装时更新：

```bash
git -C ~/.codex/skills/cc-aidev-agent-guidelines-common pull --ff-only
```

在 Codex 中可以显式调用：

```text
使用 $cc-aidev-agent-guidelines-common 查看当前组织的智能体。
```

也可以直接描述 AgentCiCi 智能体、技能、MCP 或 AI Web 应用任务，由 Codex 自动选择本 Skill。

## 前置条件

- Python 3.9 或更高版本。
- AgentCiCi 管理后台生成的开发者登录信息。
- 与任务匹配的最小 scope，例如 `agent.read`、`skill.write` 或 `application.submit`。

管理 OpenAPI 使用开发者密钥换取短期 Token。调用已发布智能体使用独立的 Agent API Key，两者不能混用。

## 登录

在 AgentCiCi 管理后台使用“复制 AI 登录信息”，然后运行：

```bash
python3 scripts/agentcici_auth.py login
```

粘贴后台复制的 Base64 文本。脚本会先向服务端验证，成功后才保存登录状态。macOS 下 Secret 保存在钥匙串中，不会写入项目文件。

```bash
# 查看本机是否已保存登录信息
python3 scripts/agentcici_auth.py status

# 清除本机保存的登录信息
python3 scripts/agentcici_auth.py logout
```

不要把 Base64 原文、Client Secret 或 Token 写入命令参数、Git 文件或日志。详见 [认证与 scope](references/authentication.md)。

## 管理 AgentCiCi 资源

### 智能体

```bash
python3 scripts/agentcici_manage.py agents list
python3 scripts/agentcici_manage.py agents get AGENT_ID
python3 scripts/agentcici_manage.py agents create --file /absolute/path/agent.json
python3 scripts/agentcici_manage.py agents update AGENT_ID --file /absolute/path/agent.json
python3 scripts/agentcici_manage.py agents compile AGENT_ID
python3 scripts/agentcici_manage.py agents publish AGENT_ID --version-no 1
```

查看和替换关联资源：

```bash
python3 scripts/agentcici_manage.py agents skills AGENT_ID
python3 scripts/agentcici_manage.py agents bind-skills AGENT_ID --file /absolute/path/bindings.json
python3 scripts/agentcici_manage.py agents bind-knowledge AGENT_ID --json '{"knowledgeBaseIds":[123]}'
python3 scripts/agentcici_manage.py agents bind-tools AGENT_ID --json '{"toolIds":["query_customer"]}'
```

详见 [智能体管理](references/agents.md)。

### 技能

```bash
python3 scripts/agentcici_manage.py skills list
python3 scripts/agentcici_manage.py skills get SKILL_ID
python3 scripts/agentcici_manage.py skills create --file /absolute/path/skill.json
python3 scripts/agentcici_manage.py skills update SKILL_ID --file /absolute/path/skill.json
python3 scripts/agentcici_manage.py skills compile SKILL_ID
python3 scripts/agentcici_manage.py skills publish SKILL_ID --change-log '初始版本'
```

详见 [技能管理](references/skills.md)。

### MCP 服务

```bash
python3 scripts/agentcici_manage.py mcp list
python3 scripts/agentcici_manage.py mcp get SERVER_ID
python3 scripts/agentcici_manage.py mcp create --file /absolute/path/mcp.json
python3 scripts/agentcici_manage.py mcp update SERVER_ID --file /absolute/path/mcp.json
```

详见 [MCP 服务管理](references/mcp-tools.md)。

> 更新前先读取当前资源。技能和 MCP 更新使用完整 `PUT`，应先合并原对象与已确认变更。删除命令必须同时传入匹配的 `--confirm-id`。

## 开发 AI Web 应用

新应用在独立目录中使用 `application.json`。最小示例：

```json
{
  "schemaVersion": 2,
  "appCode": "customer-summary",
  "name": "客户摘要",
  "version": "1.0.0",
  "summary": "为 CloudCC 客户页面生成摘要",
  "appType": "web",
  "outputDir": "dist",
  "entry": "index.html",
  "renderer": "iframe",
  "host": {
    "closeBehavior": "hide",
    "hostLayer": "content"
  }
}
```

省略 `launchers` 时，打包器默认生成 CloudCC 脚本菜单：

- 触发方式：`menu`
- 展示位置：`page-content`
- 菜单名称：应用名称
- 菜单内部标识：根据 `appCode` 生成

如需全局浮点、页面按钮或其他展示位置，再显式配置 `launchers`。入口和展示容器的完整枚举见 [应用资源清单](references/application-manifest.md)。

构建前端后执行：

```bash
python3 scripts/agentcici_application.py check --manifest /project/application.json
python3 scripts/agentcici_application.py package \
  --manifest /project/application.json \
  --output /project/release/customer-summary-1.0.0.zip
python3 scripts/agentcici_application.py validate \
  /project/release/customer-summary-1.0.0.zip
```

只有明确要求提交时才执行：

```bash
python3 scripts/agentcici_application.py submit \
  /project/release/customer-summary-1.0.0.zip
```

`submit` 只提交发布申请并尝试创建草稿，不会代替平台管理员上架。详见 [AI 应用与发布包](references/ai-applications.md) 和 [Web 应用开发规范](references/web-app-development.md)。

## 导出原生资源包

```bash
python3 scripts/agentcici_manage.py agents export AGENT_ID \
  --output exports/assistant.ciciagent
python3 scripts/agentcici_manage.py skills export SKILL_ID \
  --output exports/skill.zip
```

导出命令不覆盖已有文件。应用包中的自定义智能体必须使用原生导出包，不能用 CRUD JSON 伪造。详见 [资源包规范](references/resource-packages.md)。

## 仓库结构

```text
.
├── SKILL.md                     # Codex 技能入口与核心约束
├── agents/openai.yaml           # Codex 展示与调用配置
├── assets/                     # Web 应用入口模板
├── references/                 # 按模块加载的详细规范
└── scripts/                    # 认证、资源管理、应用打包与测试
```

## 本地验证

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
git diff --check
```

## 更多资料

- [Skill 完整工作流](SKILL.md)
- [智能体运行 OpenAPI](references/agent-runtime-openapi.md)
- [应用存储与版本清理](references/application-storage.md)

## License

本仓库尚未声明开源许可证。在复制、分发或修改前，请先向 CloudCCAI 确认授权范围。
