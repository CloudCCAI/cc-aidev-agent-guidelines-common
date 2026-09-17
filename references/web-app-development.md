# 纯前端 Web 应用规范

## 构建与站点

React、Vue 或原生前端均可，交付静态构建目录，根层必须有 index.html。不要交付 node_modules、开发服务器、SSR 服务或源码目录。资源地址相对站点目录；多页面应用应明确入口，SPA 默认使用 hash 路由，除非实际站点已验证 history fallback。在非根子路径验证 JS/CSS、图片、字体、动态加载和页面刷新，不能只测试开发服务器。

框架版本和构建参数以项目锁文件及已安装工具为准。不要引入一个未经提供或发布的 AgentCiCi SDK 包。调用层使用应用自有小模块封装，接真实平台能力前可以用明确标注的 mock；mock 成功不能写成智能体联调成功。

构建包只包含运行必需文件，排除 .env、源码映射、凭据、真实客户数据。VITE_* 等构建变量会进入浏览器，不是密钥存储。打包工具仅做文件名与结构检查，不能证明编译后代码没有敏感内容。

## 用户与智能体接入

目前真实运行接口见 [agent-runtime-openapi.md](agent-runtime-openapi.md)，使用 Agent API Key；开发者密钥用于管理，不能直接用于运行。纯前端不嵌入开发者 Secret 或长期 Agent API Key。

应用调用以逻辑 agent ref 为输入，由受信服务基于登录用户、org 和安装记录解析真实智能体。通用应用网关尚未提供，不能把此前讨论的网关当成现成 API。项目提供的 agentcici-app.js 是 CloudCC 宿主嵌入 SDK，负责安装配置、换票和 iframe，不是服务端运行网关。真实联调前核对目标环境提供的运行适配层；缺少时保留 mock 和明确阻塞，或在授权范围内实现服务端适配后再接入。已有思思 runtime 接口为特定安装方案，不自动适用于任意新应用。

静态站点可访问不代表调用已获授权。站点与 CRM 可能跨域，不能默认读取 parent 的 CCDK、Cookie 或 localStorage。嵌入式登录桥接必须核对实际接口，若采用 postMessage，双方校验精确 origin、消息来源及请求关联；不要把 CRM Token 放 URL。菜单在 CloudCC 宿主页面获取运行配置，再按下述协议传给 iframe；不得把密钥字面值写进脚本。

应用处理 loading、错误、取消与重试，卸载页面终止在途请求。会话 ID 仅复用于同一用户、org、安装实例和智能体；身份切换清空。文件上传结果只能用于所属会话权限范围。流式接口按 SSE 事件边界增量解析，支持跨网络分片，不假设一次 read 就是完整 JSON。

## 展示与生日邮件契约

桌面端先完成输入表单、生成按钮、主题/正文编辑区和复制反馈。示例契约为 `{"subject":"...","body":"..."}`，提示词约定不代表服务端强制 schema；前端校验缺失字段，保留可理解的失败反馈。用纯文本展示用户输入和模型输出，不直接注入 innerHTML。重复点击不能产生并行请求覆盖结果，重试由用户触发。

生日邮件第一期只生成草稿，不创建发送能力。真实姓名、生日或邮件正文不写入调试日志，默认不持久化。知识库是可选的企业写作依据，不是此例必需资源。

## CloudCC 站点与脚本菜单

当前站点后台已有 POST `/api/site/saveSite`、`/api/site/uploadZip`、`/api/site/querySiteDetail`、`/api/site/enableSite`。这是 CloudCC 登录接口，不是 AgentCiCi 开发者 OpenAPI。

现有保存参数包含 first、label、apiname、sitecontact、defaultrecordowner、sitepath、fullurl、description、activehomepage、inactivehomepage、isenable、zipid、zipname；负责人、组织前缀等来自目标组织。先创建站点取得 ID，再上传 ZIP。上传为 multipart，字段 `files`、`sitePath`（当前组织/站点路径）、`filesName`、`siteId`。按实际响应与查询结果确认上传成功，不把 HTTP 200 单独当作完成。

安装脚本菜单的业务 JSON 为 tabName、pname、type=script、functioncode；现有安装器按菜单接口补全目标组织简档与应用范围。站点入口运行后，安装器才能生成最终 functioncode。默认生成 CRM 内嵌菜单，参照下述宿主初始化流程。容器选择器以实际 CloudCC 环境和互动工作台实现为准，不杜撰 CCDK 方法，不移除或替换 CRM 自身节点。

## 默认菜单与 iframe 初始化（必须遵守）

创建 Web 应用时，未声明 launchers 则默认生成 `menu` 触发入口并在 `page-content` 展示；显式声明时按用户配置生成入口。菜单类型创建一个 CloudCC 自定义脚本菜单，填写 menu.tabName、menu.pname、menu.type=script 和 menu.functioncode。菜单随应用打包，不把“手动添加菜单”留给安装客户。旧menu.json格式的functioncode保留 `__AGENTCICI_SITE_URL__` 兼容标记；新schemaVersion=2通过installationManifest提供完整JS；实际站点 URL 读取 runtime.webUrl；打包工具原样保留自定义脚本。仅打开新窗口的兼容模板不满足新应用交付要求。

CloudCC 菜单、按钮和浮动入口统一加载 `frontend/public/sdk/agentcici-app@1.1.0.js`，再以 `appCode` 调用通用宿主 SDK。应用路由、认证、关闭方式和宿主层级必须声明在应用自己的 `application.json`，不要在公共 SDK 或菜单脚本中实现应用专属逻辑。

宿主执行顺序：

1. 使用 `$CCDK.CCToken.getToken()` 获取当前登录身份；setup 地址来自经确认的配置或 `window.Glod['ccex-setup']`。
2. 携带 accessToken 请求 `GET /api/agentcici/ai-applications/runtime?appCode=<固定应用代码>`，验证 HTTP 状态和响应 success/result，读取 data.apiBase、apiKey、user、agentId、keyType。appCode 由菜单固定，org 由服务端登录身份决定。未安装或缺字段时显示错误，不回退到开发者 Key。
3. 创建站点 iframe，挂载到经核实的 CRM 内容容器；保留原有 DOM 和生命周期。初始化监听器必须先于 iframe 加载注册。
4. 子页面发送 `{type:"agentcici:ready", protocolVersion:1, requestId}`。宿主核对 event.source===iframe.contentWindow、event.origin===站点URL.origin 及消息结构后，以精确 targetOrigin 返回 `{type:"agentcici:init", protocolVersion:1, requestId, context}`。
5. context 白名单为 appCode、apiBase、apiKey、user、agentId、keyType；仅业务调用确需 CRM 上下文时附加短期 cloudccContext。连接应用 Secret 留在宿主，仅用于 CCDK 换取连接应用 Token，不传给 iframe；开发者管理凭据绝不传入。
6. 子页面引入同一公共 SDK，用 `AgentCiCiApp.createClient(...)` 完成父窗口、精确 Origin、requestId 和协议版本校验。SDK 设置 `window.AgentCiCiContext` 并通过 `ready` 返回上下文。实际部署域名由宿主创建 iframe 时动态写入，子应用不预置域名白名单。

在 SDK `ready` 完成前禁用生成按钮。不要直接假设 window 属性已经存在。iframe 模式只能等待宿主消息，有超时、错误及销毁清理；不能加载测试凭据兜底。账号切换时宿主重新获取配置、重建初始化，子页面取消请求并清空旧会话。两边不使用 `*` 发送凭据，凭据不写日志、localStorage 或构建产物。

### Web 应用子页 SDK

普通 iframe 应用在 `index.html` 中先引入已部署的 `agentcici-app@1.1.0.js`，再启动业务代码。业务代码只创建一个 client：

```js
const client = window.AgentCiCiApp.createClient({
  localContext: window.__AGENTCICI_LOCAL_CONTEXT__
});

const context = await client.ready;
// context 也同步保存在 window.AgentCiCiContext。
startApplication(context);

const unsubscribe = client.subscribe(nextContext => {
  updatePageContext(nextContext.pageContext);
});

// 页面卸载时：
unsubscribe();
client.destroy();
```

- 发布嵌入模式：SDK 从宿主添加的 `agentciciParentOrigin` 读取当前宿主 Origin，仅向该精确 Origin 发起握手，并且只接受 `event.source === window.parent` 且 `event.origin` 精确相同的回复。不得使用 `*`。
- 上下文更新：SDK 自动处理 `agentcici:context`，更新 `getContext()` / `window.AgentCiCiContext` 并调用 `subscribe()` 监听器。需要宿主重新换取 runtime 时调用 `client.refresh()`；请求宿主关闭容器时调用 `client.close()`。
- 本地模式：仅当页面为顶层且 hostname 为 `localhost`、`127.0.0.1` 或 `[::1]` 时，SDK 才接受显式 `localContext`。它应由未提交的本地文件或开发服务器运行时注入；不得把真实 Key 写入源码、`.env` 的前端变量或构建产物。
- 顶层非 localhost 页面、缺失宿主 Origin、消息来源不匹配或超时都必须显示明确错误，不得回退到测试 context。

独立本地测试：仅在顶层页面且显式 development 模式下读取测试用 `window.AgentCiCiContext`；从不提交 Git 的本地配置或交互输入提供运行 Key。生产顶层打开而无可信上下文时提示从 CloudCC 菜单进入。URL 可携带 appCode、locale 等普通参数，不能携带 API Key、Token、Secret（query 和 hash 均禁止）。动态传入运行 Key 意味着该应用脚本可读取它，不得宣称此模式把 Key 隐藏在服务端。

验收：默认菜单已打包；跨域 iframe 正常初始化并使用当前客户配置；本地测试正常；无身份/未安装/错误来源/超时有明确反馈；切换客户不复用旧 Key 或会话；源码、菜单和应用 ZIP 不含真实凭据。自动资源安装未完成时，明确说明 runtime 配置仍需安装流程生成，不能把前端初始化成功当成安装成功。

## 发布站点到 Nginx

平台发布版本时将 Web ZIP 解压到共享 aiapp 目录，访问路径为 `/aiapp/{appCode}/{version}/{sha256}/index.html`。多 Web 包分别生成路径；安装清单 webApps 保存站点路径，setup 安装记录保存后，runtime 返回 webApps 和默认 webUrl（第一项）。旧安装需升级/重装，不能猜测地址代替 runtime 配置。

打包工具默认使用 assets/application-menu.js 短加载器，加载 agentcici-app.js 后执行 AgentCiCiApp.mount({appCode})。SDK 负责 CCDK 登录身份、runtime、连接应用换票、iframe 与初始化消息。menu.sdkUrl 可覆盖 SDK 地址，默认 https://uat.agentcici.com/sdk/agentcici-app.js；发布前确认环境已有该 SDK。自定义 functioncode 仍可覆盖，但必须遵守相同初始化要求。当前使用一个 Web 应用入口，由安装的 renderConfig.entryUrl 或 runtime.webUrl 决定。子页面统一使用 SDK `createClient()`，不再复制协议实现。

站点发布与 org 资源安装是不同阶段；静态文件就绪不代表智能体/技能已经安装。部署需要 backend 可写与 Nginx 只读的共享目录，以及 /aiapp/ 路由。平台上架权限保持管理员专有。


## CRM 内容区嵌入与清理

默认菜单使用 `assets/application-menu.js`，嵌入 `.console-right-content`，使用 prepend 添加自身 section，不覆盖 CRM 节点，不创建全屏遮罩或额外关闭按钮。iframe 允许 clipboard-write，宽度100%，高度依据容器高度与视口剩余空间取较小值。

- 使用 `window.AgentCiCiAppEmbed.destroy()` 销毁上一个实例，再创建本次实例，所有应用采用同一宿主实例入口。
- 先获取 runtime 配置，再创建 iframe；postMessage 继续校验来源窗口、精确 origin、协议版本和 requestId，凭据不进入 URL。
- 监听 resize/ResizeObserver；监听 hashchange、popstate、pagehide，并每200ms比较入口URL，以覆盖 SPA 路由变化。
- MutationObserver 等待内容区出现；目标被移除、宿主被移走，或目标出现其他直接子节点时销毁实例。10秒仍找不到内容区时清理并提示重新打开应用。
- destroy 必须中止请求、断开观察器、清理定时器和事件监听、移除自身节点；异步返回后检查 destroyed，避免切换页面后旧实例重新挂载或弹错。
- 验证重复点击、切换菜单、容器延迟出现、窗口缩放及请求中切换页面。模板中的 appCode 由打包工具替换，禁止硬编码为邮件助手。

## 统一宿主 SDK

项目已提供 `frontend/public/sdk/agentcici-app.js`。菜单、详情脚本按钮及悬浮入口统一调用 `AgentCiCiApp.mount({appCode, name})`，位置由安装的 renderConfig.positions 决定（float/right/fullscreen/detail-right/list-right/dialog/home）；完整参数与现有应用适配见同目录 README.md。入口不再内联 runtime 请求、CCDK 换票或 iframe DOM。

普通页面继续使用上述协议，context 额外提供 display、pageContext；存在连接应用时附加 cloudccContext。业务关闭方式、宿主层级和 CloudCC SSO 票据参数必须由各应用的 host 清单声明，公共 SDK 只执行通用协议，不识别具体 appCode、业务路由或票据前缀。Shadow DOM 应用通过 register 挂载，普通 React/Vue 应用继续使用 iframe，无需增加嵌入构建。SDK 已实现不代表目标环境已部署；不得在菜单里嵌入真实密钥。

应用版本「安装内容」使用最新 renderConfig：renderer 为 iframe 或 shadow-dom，entryUrl 为入口地址，positions 为有序多选（第一项默认），并包含必填 closeBehavior 与 hostLayer，以及可选 authentication。安装成功后 setup-svc 保存快照，通过 appCode 返回。CRM 客户端脚本由清单生成，加载固定 agentcici-app@1.1.0.js 后仅传 appCode；公共 SDK 为所有应用创建同一种全局浮点入口，并读取安装配置中的名称、图标和位置。setup-svc读取并保存完整清单，根据steps创建对应CRM资源；缺少最新配置直接报错，不回退旧模型。
