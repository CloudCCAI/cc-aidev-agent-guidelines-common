# 资源清单与发布前问答

每个应用一个独立目录，建议 applications/<appCode>/：application.json、src/、scripts/、构建目录dist/和产物release/。源码/清单纳入版本管理；dist/release忽略。保留旧版本产物用于追溯，不覆盖相同版本。

## 必填与条件项

- schemaVersion固定2；appCode全局唯一；name名称；version三位0–9、逢9进位；summary非空描述。
- appType固定web；outputDir为单个构建目录，根层必须有index.html；entry为包内相对入口或完整HTTP(S)地址；renderer=iframe/shadow-dom。JS应用需实现AgentCiCiApp.register挂载协议。
- host 为必填对象，使用最新统一宿主协议：closeBehavior 只能是 hide/confirm-destroy，hostLayer 只能是 content/assistant。需要 CloudCC SSO 票据的 iframe 应用在 host.authentication 中声明 type=cloudcc-sso-ticket、query、targetPath、ticketPrefix 和可选 localeParam；这些业务值属于应用清单，公共 SDK 不按 appCode 写死。
- connectedApplications可选布尔，缺省为true并创建连接应用；只有用户明确不需要 CloudCC 身份/OpenAPI 时才写false。不要扩展为客户端权限对象。
- agent可选且最多一个：platform包含type/ref，引用当前org开户已有实例；不能附file/skills/knowledges以重绑客户资源。custom包含type/ref/file，skills每项ref/file/bindingRef，knowledges每项ref/name/bindingRef。bindingRef来自原生智能体导出的依赖ref。可选keyType为cloudcc或standard，缺省cloudcc；需要直接调用智能体且不传CloudCC页面令牌时使用standard。
- launchers 可选；Web 应用未声明时，打包器默认生成一个 `menu` 入口，展示位置为 `page-content`，菜单名使用应用名称，内部标识由 appCode 安全生成。显式提供时必须是非空数组；每项id（稳定且唯一）、name、trigger、positions（有序）、payload（查询确认的CRM安装字段）；可选icon/order/objects/placement。默认不需要file：打包器生成完整启动JS，仅传appCode；名称、图标与展示位置由SDK从安装快照获取。file仅用于确有业务自定义脚本的场景，必须位于应用目录内，内容原样打包。菜单图标和排序须映射为CRM payload字段，不能假定各入口字段相同。
- installationManifest 同时保存 application（appCode/name/summary）、launchers（入口元数据）、renderConfig 和 steps（完整JS与资源字段）。SDK地址占位符 `__AGENTCICI_SDK_URL__` 由setup-svc根据服务端AgentCiCi域名解析，不需要客户填写name/icon/position或硬编码环境域名。
- 同一应用每种trigger最多配置一项；这一项可配置多个不重复的positions，第一项为默认位置，其余可切换。入口id仍用于安装资源回执，不需要额外向SDK传launcherId。

## trigger：触发方式

| 类型 | 含义 | CloudCC安装资源 |
| --- | --- | --- |
| global-floating | 全局浮点入口 | 全局客户端脚本，由SDK创建浮点 |
| create-button | 新建页底部按钮 | 客户端脚本 |
| edit-button | 编辑页底部按钮 | 客户端脚本 |
| menu | 自定义菜单入口 | 自定义脚本菜单 |
| detail-button | 详情页按钮 | 自定义脚本按钮 |
| list-button | 列表页按钮 | 自定义脚本按钮 |

对象相关入口必须提供客户确认的objects及对应CRM payload。先通过CloudCC开发技能查询对象再请客户选择，不编造对象ID。新建/编辑页底部按钮需要提供已实现页面生命周期与按钮挂载的业务脚本file，公共SDK不猜测CRM表单DOM。

脚本字段按资源类型区分：客户端脚本使用 scriptContent，菜单使用 functioncode，按钮使用 tpSysButtonVO.functionCode（大写 C）。打包后核对非空脚本，安装后读取按钮确认保存内容，不能仅以资源 ID 返回判定脚本可用。

## 详情按钮的布局分配

`objects` 指定入口对象范围，`payload.objid` 是实际安装对象标识；`positions` 只控制应用窗口打开后的展示位置，不会把按钮加入 CRM 页面布局。

- 用户要求详情页可用的按钮时，应明确布局分配范围。当前安装器支持在 launcher 上配置 `"placement": "allObjectDetailLayouts"`，编译后进入对应 `installationManifest.steps[].placement`，安装时将按钮加入目标对象的全部详情布局。
- 缺少 placement 时仅创建按钮，不自动分配布局。仅当用户选择手动分配时才有意省略，并在交付中说明；用户只要求指定布局时，不擅自扩大到全部布局，当前该字段不支持指定布局列表。
- 此值仅用于 detail-button，且 payload 必须有真实 objid、tpSysButtonVO.btnType=detailBtn、category=CustomButton；不得照搬到列表、新建或编辑入口。
- 发布前检查生成的安装步骤确实保留 placement；安装后检查资源回执 layoutIds 和目标详情布局中按钮可见，不能仅检查按钮资源存在。
- 已发布版本不可覆盖。补配需使用新版本；本地修改不会修复已安装布局。现有 setup-svc 对已有按钮升级会报“已有按钮暂不支持升级”，应先核对目标环境支持，再确定补分配或重新安装方案，不承诺升级会自动修复。

入口配置片段（其余必填字段仍需补齐）：

```json
{
  "trigger": "detail-button",
  "positions": ["detail-right", "fullscreen"],
  "placement": "allObjectDetailLayouts"
}
```

## positions：展示位置

| 清单类型 | 含义与生命周期 | SDK内部值 |
| --- | --- | --- |
| global-floating | 可拖动浮窗，跨页面保留 | float |
| global-right | 全局右侧占位，跨页面保留 | right |
| detail-right | 详情页右侧占位，离开当前详情页隐藏或清理 | detail-right |
| list-right | 列表页右侧占位，离开当前列表页隐藏或清理 | list-right |
| dialog | 居中模态弹窗，关闭后隐藏 | dialog |
| page-content | 菜单对应内容区，离开菜单销毁 | home |
| fullscreen | 网页视口内全屏，覆盖CRM区域；不是浏览器原生全屏 | fullscreen |

trigger里的global-floating表示小浮点入口，positions里的同名值表示打开后的浮窗，两者职责不同。

全局浮点入口的外观、二维拖动、打开隐藏、关闭恢复和销毁由公共 SDK 统一实现；应用只能提供入口 name/icon，不提供业务专属入口样式或拖动规则。

```json
{
  "trigger": "global-floating",
  "positions": ["global-floating", "global-right", "fullscreen"]
}
```

以上为单个入口的类型配置片段；完整入口还需id/name/payload等字段。该例默认浮窗，可切换右侧或全屏。

多入口定位约定为appCode + trigger，名称、图标、展示位置仍从安装快照读取。当前SDK尚未实现按trigger选择入口配置，现有生成器仍使用应用级renderConfig；不能把这一约定当作已完成的多入口运行能力。需要多入口各自使用不同位置时，先核对并补齐目标SDK支持。

## 问答流程

1. 先读已有清单、代码、导出包和会话中已确认信息，执行check。不问已知答案。
2. 首轮只问应用标识/名称/描述/候选版本的缺失项；可展示建议值，让客户确认。确认版本需结合平台已有版本，不自行覆盖。
3. Web 应用未指定入口时直接使用默认的 `menu` + `page-content`，不再追问；只在用户要求其他入口或展示位置时确认具体配置。再确认是否引用智能体；连接应用默认创建，不单独询问，只在用户明确要求关闭时设为false。对象相关入口调用CloudCC开发技能读取实际对象候选，再请客户选对象；无法查询时明确等待对象信息，禁止编造ID。
4. 对条件缺失项定向提问：平台智能体ref，或自定义智能体导出包和真实依赖；加载入口及目标环境是否已部署固定版本SDK。密钥通过登录工具处理，不写入清单。
5. 每轮将回答写回application.json。check返回missing为空后继续构建、package、validate；存在缺失则停止上传，继续不依赖答案的本地工作。
6. 上传前展示appCode/version、资源类型、入口/展示位置、连接应用开关及目标环境。只有用户请求提交时submit；仅请求开发/准备时交付包。上架仍要求平台管理员身份，不能用开发者Token越权。

示例问法：
“还缺应用描述和展示位置。请补充一句用途说明；菜单点击后是在内容区打开，还是弹窗打开？”
“已查询到客户、联系人、商机对象。这个详情页按钮需要安装在哪些对象？”

源清单填写完成只说明信息完整，不等于已部署接口、已上架或真实客户安装成功。测试证据与真实业务验收分别报告。
