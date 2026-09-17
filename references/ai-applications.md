# AI 应用与发布申请包

新应用使用 [源清单与发布前问答](application-manifest.md)。源清单保存于应用自己的目录，由工具生成 ZIP 内的 application.json；源清单不被覆盖。

## 提交与权限

- `check` 检查源清单缺失字段；`package` 构建申请 ZIP；`validate` 校验；`submit` 上传并尝试创建草稿；`draft` 单独重试草稿；`status` 查询申请。
- POST `/openapi/v1/management/application-requests`，multipart file，需要 application.submit。
- GET `/openapi/v1/management/application-requests/{id}` 与 `/{id}/download`，需要 application.read，只允许本组织。
- POST `/openapi/v1/management/application-requests/{id}/draft`，需要 application.submit。开发者只能创建本组织所有应用的草稿，不能认领平台应用或其他组织应用，不能上架。
- 平台管理员可用 POST `/platform/application-requests/{id}/draft` 将已提交包建立为平台应用草稿（仅新平台应用或原平台所有应用）。再走平台现有版本发布接口；开发者Token不能调用这两个平台操作。
- 同 org + ZIP SHA256 幂等；结果未知时重交原包，不重新打包冒充同一次重试。相同版本不可用不同包覆盖，已发布版本不可修改。
- 对既有平台思思的开发者提交可能上传成功、自动草稿被拒绝；保留申请ID交平台管理员，不更改appCode所有权或扩大开发者权限。

包存储、OSS和最多5个版本清理见 [存储规范](application-storage.md)。开发者不需要OSS密钥。申请SUBMITTED、草稿DRAFT和市场已发布是不同状态。

## 包内协议与兼容

外层仍为 `format=agentcici-application-request, formatVersion=1`。含 application.json、单个 site.zip（根层index.html）、自定义智能体 agents/<ref>.ciciagent、独立技能 skills/<ref>.zip。新清单入口代码写入 installationManifest.steps；仅旧menu格式额外生成 cloudcc/menu.json。sha256覆盖所有外层文件，application.json自身除外，原生包字节不变。

平台智能体使用可选platformAgent={ref}，agents为空；不打包它已有的托管技能/知识库。不需要智能体时agents为空且无platformAgent。自定义智能体仍完整校验导出依赖映射，不支持工具依赖或托管技能伪造导出。知识库定义至少ref/name，客户文档不随包上传。

旧源清单web.directory、agents/skills/knowledgeBases/menu仍可打包；新应用只使用schemaVersion=2。新源清单appType=web，不接受开发者自行声明官方发布身份。官网身份由平台管理员创建草稿时确定。

## 发布与安装

上传解析资源清单并持久化；查询不反复下载解压。平台发布将site.zip解压至Nginx aiapp/<app>/<version>/<摘要>/，目录755、文件644。renderConfig.entryPath为包内相对入口，发布确认文件存在；安装后setup用当前环境地址和已安装webUrl生成完整entryUrl。外部入口使用entryUrl。新入口解析要求部署本次AgentCiCi与setup代码。

setup调用已发布版本的安装清单和 POST `/openapi/v1/management/ai-applications/{app}/versions/{version}/install-resources`，需要application.install。自定义资源在当前org创建并绑定；平台智能体按ref读取当前org实例及已发布版本，不导出或覆盖客户修改。平台智能体不存在、无权限或未发布时明确失败，不跨org取资源。每个应用最多一个智能体和一个Web应用。

connectedApplications是可选布尔开关，缺省为true，转换为requiresConnectedApplication；setup为true时创建连接应用。只有用户明确不需要 CloudCC 身份/OpenAPI 时才设为false。运行时由宿主换取OpenAPI token，Secret不传入应用、Key和token不放URL。安装steps携带完整客户端脚本/菜单/按钮源码，由setup-svc固定适配器执行，setup-web只请求 /install 或 /uninstall。pendingManifest保存本次安装清单，installationManifest在成功后保存完整已安装快照；runtime只返回application/launchers/renderConfig等运行字段，不返回完整脚本清单。每步资源ID存入resources，首次安装失败按记录自动清理；升级失败保留升级失败状态和已有资源，不能当成首次安装删除。真实安装验收与本地验证分别记录。

## 常用命令

```bash
python3 scripts/agentcici_application.py check --manifest /project/application.json
python3 scripts/agentcici_application.py package --manifest /project/application.json --output /project/release/app-1.0.0.zip
python3 scripts/agentcici_application.py validate /project/release/app-1.0.0.zip
python3 scripts/agentcici_application.py submit /project/release/app-1.0.0.zip
python3 scripts/agentcici_application.py status REQUEST_ID
```
