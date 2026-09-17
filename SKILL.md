---
name: cc-aidev-agent-guidelines-common
metadata:
  version: "1.4.7"
description: 使用开发者密钥管理 AgentCiCi 组织内智能体、技能和 MCP；指导纯前端 AI 应用开发、CloudCC 站点与脚本菜单集成，并将前端产物、原生智能体包和技能包整理为发布申请 ZIP 并提交到已部署的接收接口。用于平台资源管理、应用开发与申请包准备；自动安装须先核对服务端能力。
---

# AgentCiCi 平台管理

当前技能版本：`1.4.7`。

本 Skill 同时服务两个阶段：设计阶段先理解模块职责与边界，实施阶段再调用明确的管理 API。不要在不了解现有资源的情况下直接写入。

## 技能版本号规范

- 技能版本统一为 `X.Y.Z`，三段均为一位数字 `0–9`，格式为 `^[0-9]\.[0-9]\.[0-9]$`，不使用多位数字或预发布后缀。
- 每次技能更新从最右位递增；该位为 9 时归零并向左进位，例如 `1.2.8 → 1.2.9 → 1.3.0`、`1.9.9 → 2.0.0`。
- 同步更新 frontmatter 的 `metadata.version`、正文版本及本地安装副本。系统内部的数字版本 ID 不受此规则影响。
- `9.9.9` 已达此格式上限，后续版本规则由用户决定，不回绕或重复使用旧版本。

## 入口类型与展示位置

完整枚举、生命周期及示例见 [资源清单类型](references/application-manifest.md)。支持6种trigger与7种positions（包括fullscreen网页内全屏）。同一应用每种trigger最多一项，每项positions可多选且不重复，第一项默认。发布前按该表与客户确认，不将触发入口和展示容器混为一谈。appCode + trigger是多入口定位约定；当前SDK按trigger选配置的实现状态见该文档，不宣称未实现的能力。

## 应用入口与安装职责

新应用的入口脚本只向 `agentcici-app@1.1.0.js` 传 `appCode`，不要传 name/icon/position。名称、图标、触发方式与展示位置保存到资源清单；公共 SDK 按 appCode 请求 setup runtime 的已安装快照。全局浮点使用 `start({appCode})`，菜单/脚本按钮使用 `mount({appCode})`。入口浮点、拖动、去重和清理属于公共 SDK，不在每个应用复制一份。

普通 iframe Web 应用也必须在子页面引入同一 SDK，用 `AgentCiCiApp.createClient(...)` 获取宿主上下文；不再自行实现 `message` 监听、requestId 关联、超时或来源校验，也不要预置部署域名白名单。本地模式仅在顶层 localhost 页面显式传入 `localContext`。完整用法与验收见 [Web 应用开发](references/web-app-development.md#web-应用子页-sdk)。

新 AI 应用默认创建并绑定 CloudCC 连接应用：源清单省略 `connectedApplications` 时按 `true` 编译，安装清单生成 `requiresConnectedApplication=true`。只有用户明确要求不创建、且应用不需要 CloudCC 用户身份或 OpenAPI 能力时，才显式设为 `false`。

打包工具默认生成完整启动 JS，放入 installationManifest.steps 的 scriptContent/functioncode；application/launchers/renderConfig 一起随包提交。setup-svc 安装时保存清单，解析 SDK 地址占位符并按固定资源类型创建客户端脚本、菜单、按钮；setup-web 只预览和发起安装，不再代为调用资源创建接口。旧版本安装不会自动获得新入口配置，需要发布新版本并升级。

详情页按钮的创建与布局分配是两个步骤。发布前按 [清单规范](references/application-manifest.md#详情按钮的布局分配) 核对 placement，不能把 positions 当成按钮布局配置，也不能以按钮创建成功代替页面可见验收。

## 入口脚本的 JS 缓存刷新

生成客户端脚本、菜单脚本、按钮脚本时，所有动态加载的 JS（包括 SDK）的 URL 都必须在加载时追加时间戳查询参数：使用 `new Date().getTime()`，不能在生成或打包时写死。自定义 `file` / `functioncode` 也遵守此规则。保留原有查询参数和 hash，推荐：

```js
const url = new URL(src, document.baseURI);
url.searchParams.set('_t', new Date().getTime());
script.src = url.href;
```

保留已有 SDK 单例和加载去重；时间戳用于实际发起 JS 请求时刷新缓存，不要求重复加载已初始化 SDK。

## 前置配置

优先使用管理后台“复制 AI 登录信息”得到的 Base64 文本。收到这类文本或用户要求登录/记住登录时，先读 [references/authentication.md](references/authentication.md)，通过 `python3 scripts/agentcici_auth.py login` 的标准输入或不回显交互输入传入，不把真实值写入命令参数、项目文件或回答。

- Base64 解码后是三项 export 声明，脚本按数据解析，绝不 source/eval/执行它。
- 登录先调用 `/openapi/v1/developer/token` 验证，成功才保存。macOS 使用钥匙串保存 Secret，`~/.config/agentcici/login.json` 仅保存地址、Client ID 和钥匙串引用。
- 下次管理或应用提交命令自动读取保存的身份，并自动换取短期 Token；Token 只在进程内缓存。
- `python3 scripts/agentcici_auth.py status` 查看保存状态（不代表服务端凭据仍有效）；`logout` 清除本机保存信息，不撤销服务端凭据。
- 环境变量方式仍可用，必须同时设置 AGENTCICI_BASE_URL、AGENTCICI_CLIENT_ID、AGENTCICI_CLIENT_SECRET；优先于保存身份，禁止混合两组身份字段。非 macOS 暂用环境变量，不静默明文落盘。
- 用户未提供登录信息时先检查保存状态；缺少时引导复制，不要求每次重新提供密钥。
- 管理 OpenAPI 不使用 Keycloak，也不接受单智能体运行 API Key。Secret 和 Base64 原文均按凭据处理，不写日志。

## 选择模块

- AI 应用开发或发布申请包：先读 [references/ai-applications.md](references/ai-applications.md)，开发前端时再读 [references/web-app-development.md](references/web-app-development.md)。使用 `scripts/agentcici_application.py check|package|validate|submit|draft|status`；本地打包成功不代表已提交、已发布或可自动安装。
- 智能体/技能上传下载及知识库依赖：读 [references/resource-packages.md](references/resource-packages.md)。保留原生包，不用 CRUD 返回 JSON 冒充导出包；后台登录接口不能使用开发者 Token 冒充登录身份。
- 智能体设计、CRUD、关联资源或编译发布：先读 [references/agents.md](references/agents.md)，实施时运行 `scripts/agentcici_manage.py agents ...`。
- 调用已发布智能体：读 [references/agent-runtime-openapi.md](references/agent-runtime-openapi.md)。这套运行 API 使用 Agent API Key，不使用开发者密钥。
- 技能设计、CRUD 或编译发布：先读 [references/skills.md](references/skills.md)，实施时运行 `scripts/agentcici_manage.py skills ...`。
- MCP 服务设计或 CRUD：先读 [references/mcp-tools.md](references/mcp-tools.md)，实施时运行 `scripts/agentcici_manage.py mcp ...`。
- 换票、scope、错误语义：读 [references/authentication.md](references/authentication.md)。

只读取当前任务所需的参考文件。

## Web 应用默认交付

新建 AI 应用使用独立目录与 `application.json` 资源清单。Web 应用未声明 `launchers` 时，默认生成 `menu` 触发入口并以 `page-content` 为默认展示位置，不再要求客户确认这个默认值；客户显式配置 launchers 时按其选择生成客户端脚本、菜单或按钮入口，不额外强制创建菜单。宿主获取当前 org 的 runtime 配置，通过 SDK 挂载 Shadow DOM 应用或经校验的 postMessage 注入 iframe；应用初始化兼容 iframe 与显式本地测试模式。具体协议与验收见 [references/web-app-development.md](references/web-app-development.md)。不能在菜单或 URL 中写入真实 Key，也不能仅交付 window.open 菜单。

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

应用包必须且只能包含一个 Web 应用；智能体可选且最多一个，技能可包含多个。平台智能体引用当前 org 已有实例，不要求导出其托管技能；自定义智能体使用原生导出包并完整映射依赖。

## 发布前问答

准备或发布 AI 应用时，先读 [清单与问答规范](references/application-manifest.md)。读取现有清单及客户已确认信息，运行 `check --manifest ...`，只问仍缺失或冲突的必填项，分组提问并将回答写回应用目录的清单。对象相关入口先用 CloudCC 开发技能查询实际对象，再让客户选择；不猜测对象 ID、已有资源 ref 或发布版本。不请求用户重复提供已确认信息。

缺失项未补齐前可继续开发和只读检查，但不得上传或声称可发布。补齐后构建、打包、校验并展示实际清单与资源摘要。开发者权限仍只允许提交和创建草稿；平台上架由平台管理员执行，不增加开发者上架权限。
