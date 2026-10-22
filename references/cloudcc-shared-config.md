# 多应用共用CRM配置，源码保留在应用内

## 文件职责

项目根目录只保存一份 cloudcc-cli.config.json 和一份 .cloudcc-cache.json，多应用共用；AgentCiCi的cloudcc-agentcici.config.json也位于根目录。CLI配置/缓存不再放入每个应用，不复制或定期同步多份凭据。对象定义、自定义类、Web、需求设计和测试文档继续位于 applications/<appCode>/ 内。

CloudCC CLI当前将配置、缓存与类源码定位绑定到projectPath：配置/缓存位于projectPath根，类位于projectPath/backend/classes。create classes则直接使用当前工作目录创建源码，不能靠增加一个位置参数改变目录。因此不能将所有类命令直接改成在项目根目录执行，否则会把类代码创建到根目录。

本技能提供agentcici_cloudcc_class.py适配入口，不修改CloudCC CLI：

- create：在应用工作目录调用CLI创建backend/classes/<ClassName>，不需要在应用内放CRM配置。
- format/validate/publish：短暂将根目录backend/classes/<ClassName>映射到应用内的真实类目录，CLI以项目根目录为projectPath，从根读取/刷新配置与缓存，对映射中的应用源码执行原生操作。类级config.json的远端ID和版本仍由CLI写回应用内。
- 执行结束（包括普通失败）在finally中清理临时映射和本次创建的空目录；不移动、复制类代码或凭据，不覆盖根目录既有同名资源。被强制终止时可能留下映射，再次运行会报路径冲突；确认无操作在运行且链接目标为该应用后，只清理残留符号链接，不删除链接目标。
- 必须保持本机文件系统支持符号链接；平台不支持或拒绝创建时明确报错，不回退到复制配置/缓存或搬迁代码。多个应用使用不同业务类API Name；正在使用同名映射时拒绝并发覆盖。

## 使用方式

下列路径按用户项目和已安装技能位置替换，不使用全局CLI：

```bash
python3 /installed/agentcici/scripts/agentcici_cloudcc_class.py \
  --cli /installed/cloudcc/tools/bin/cloudcc \
  --root /project --app story-expander create StoryService

python3 /installed/agentcici/scripts/agentcici_cloudcc_class.py \
  --cli /installed/cloudcc/tools/bin/cloudcc \
  --root /project --app story-expander validate StoryService

python3 /installed/agentcici/scripts/agentcici_cloudcc_class.py \
  --cli /installed/cloudcc/tools/bin/cloudcc \
  --root /project --app story-expander publish StoryService
```

format使用相同入口，可显式--write/--check，缺省只检查。创建前仍须先读资源介绍和开发指南，不覆盖已有类；代码仅编辑应用内SOURCE区域。发布是实际开发组织写操作，须在本次开发授权范围内执行；本地验证成功不代表发布或CRM业务联调成功。

对象、字段、provider诊断、环境切换和OpenAPI等不依赖应用类目录的操作，直接使用安装CLI，按各命令的参数顺序明确传项目根目录。比如：

```bash
/installed/cloudcc/tools/bin/cloudcc doctor provider /project
/installed/cloudcc/tools/bin/cloudcc use config dev /project
/installed/cloudcc/tools/bin/cloudcc plan msapi /project fields @/project/applications/story-expander/cloudcc/metadata/content.json create
/installed/cloudcc/tools/bin/cloudcc apply msapi /project PLAN_ID
/installed/cloudcc/tools/bin/cloudcc get fields /project OBJECT_API_NAME
```

`PLAN_ID` 替换为本次返回的真实计划 ID，`OBJECT_API_NAME` 替换为字段定义所属的对象 API 名；核对计划后执行 apply，再回读字段。plan只是计划，真实执行继续按专用技能apply规则。元数据输入文件可位于应用内，使用绝对路径，不能因配置位于根目录就移动定义。应用打包继续从该应用目录读取资源，不需要从根目录跨界导入源码。

## 启动、本地联调与已有项目

- 启动时先确定用户项目根目录，分别核对两套配置的use、地址、组织和身份；它们是不同产品的凭据，不能互换或仅凭环境名相同视为同一身份。启动/调试进程从根目录.cloudcc-cache.json按当前CRM配置选取accessToken；CLI刷新仍写回根目录。
- 所有应用共享CRM当前环境，切换根配置use会影响后续所有应用。一次联调保持明确的环境，不并发切换同一配置；不要同时运行会互相覆盖同一根缓存的刷新操作。
- 根.gitignore排除cloudcc-cli.config.json、.cloudcc-cache.json和cloudcc-agentcici.config.json。配置与缓存设为本机受限权限；根目录临时类映射不提交、不打包，CLI退出后检查已清理。
- 旧项目若凭据在应用内，先确认项目根与现有两边环境；根缺配置时归并到根；已有配置时合并不冲突环境，同名环境值冲突必须明确处理，不能覆盖。验证根配置后再移除已归并的应用内凭据，代码及类级config.json不移动。缓存按CLI机制在根重建，无需合并旧Token，不为迁移伪造或改写缓存身份。
- 不因本技能更新自动查找或搬迁用户其他项目的真实配置。只有操作具体项目时按上述规则归并，缺少路径或存在身份冲突时说明具体问题。
