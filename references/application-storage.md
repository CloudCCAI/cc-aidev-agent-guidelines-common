# 申请包文件存储（服务端配置）

默认使用 OSS；本地调试必须显式选择 local。当前桶 devconsole-bucket 位于杭州，桶是 public-read；本应用 ZIP 上传时独立设为 private，不修改桶权限。压缩包不进入数据库、Git 或前端 public 目录。数据库只保存申请元数据、provider 与对象 key。服务端权限校验后下载附件，不永久保存预签名 URL。提交者不能指定对象路径或远程下载 URL。

Spring 配置键及对应环境变量：

| 配置 | 环境变量 | 说明 |
|---|---|---|
| app.application-packages.provider | APP_APPLICATION_PACKAGES_PROVIDER | oss（默认）或 local（仅显式调试） |
| app.application-packages.local-directory | APP_APPLICATION_PACKAGES_LOCAL_DIRECTORY | 默认 ./data/application-packages，需持久卷 |
| app.application-packages.oss.endpoint | APP_APPLICATION_PACKAGES_OSS_ENDPOINT | 默认 https://oss-cn-hangzhou.aliyuncs.com |
| app.application-packages.oss.bucket | APP_APPLICATION_PACKAGES_OSS_BUCKET | 默认 devconsole-bucket；应用对象私有 |
| app.application-packages.oss.access-key-id | APP_APPLICATION_PACKAGES_OSS_ACCESS_KEY_ID | 仅服务端安全注入 |
| app.application-packages.oss.access-key-secret | APP_APPLICATION_PACKAGES_OSS_ACCESS_KEY_SECRET | 仅服务端安全注入 |

项目 application.yml 已显式映射上述环境变量。

对象 key 为 `AI-App/<appCode>--<组织 SHA-256>/<version>/<申请 UUID>.zip`。应用代码是稳定名称，组织后缀避免同名应用跨组织清理。所需权限仅该前缀 PutObject/GetObject/DeleteObject 与对象 ACL 设置，开发者不需要 OSS 密钥。

每次新包持久化成功后，按本组织本应用的各版本最近成功上传时间保留最新 5 个不同版本；同版本的多个申请包属于同一版本。清理只删除数据库记录的准确 object key，不递归删除用户目录，也不清理其他应用、组织或 Nginx 已发布文件。PostgreSQL advisory lock 将同组织同应用的上传与清理串行化，支持多实例。清理前状态为 CLEANUP_PENDING，删除完成为 EXPIRED；记录仍可查询，文件不再下载。失败保留 pending 状态并返回“新包已保存，历史清理未完成”；重交同一原包可续清理，不重复上传。

OSS 未配置、上传失败不降级本地；申请记录不报告 SUBMITTED。更换 provider、Bucket 或 Endpoint 前迁移旧对象；当前记录不保存多套存储连接配置，不能直接切换后继续读取旧文件。数据库与对象存储备份/生命周期需配套；进程在对象上传后、数据库写入前崩溃可能留下孤立对象，清理时以记录核对并设置宽限期，不能按前缀直接全部删除。

已使用指定账号验证 devconsole-bucket 的私有上传、读取和删除，临时文件已清理。参考 [阿里云 OSS Java SDK](https://help.aliyun.com/zh/oss/developer-reference/oss-java-sdk/)。单个公开访问链接不能代替完整写入配置。


本机服务端配置已保存到 `~/.config/agentcici/oss-application-packages.yaml`（600，仓库外），运行服务时通过 `SPRING_CONFIG_ADDITIONAL_LOCATION=file:/Users/xuhm/.config/agentcici/oss-application-packages.yaml` 加载。此路径仅用于当前开发机；服务器部署通过上述环境变量或服务器自身私密配置注入，不能沿用开发机路径。源码修改与私密配置不代表已重启或部署运行服务。上传路径/保留策略需要 V153 迁移与新后端生效。
