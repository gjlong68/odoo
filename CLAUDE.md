# Odoo 20 企业定制开发工作区

## 项目概况

- Odoo 20.0 Enterprise（`20.0+e-20261007`），社区与企业代码合并放在 `odoo/addons/`（没有单独的 `enterprise/` 目录）。
- Python 3.12.3，虚拟环境 `odoo-venv/`；PostgreSQL 16.15，主库 `Goody`（已安装 194 个模块，含 `studio_customization`）。
- 定制模块统一放在 `custom/<module>/`；`oca/`、`app3/`、`web/` 也在 `addons_path` 中。
- 启动：`odoo-venv/bin/python odoo-bin server -c odoo20.conf -d Goody --dev=xml`
- 详细规范：`docs/odoo20-development-standards.md`；工作流：`docs/development-workflow.md`；企业定制规则：`docs/enterprise-customization.md`。

## 硬性规则（必须遵守）

1. **绝不修改 `odoo/`**。它是上游核心/企业源码，只读。所有定制通过 `custom/` 中的 `_inherit`、`_inherits`、视图 xpath、assets 扩展。PreToolUse hook 会阻止写入；确需临时修改时显式设置 `ODOO_ALLOW_CORE_EDIT=1`。
2. **不修改 `odoo20.conf`、`/etc/odoo20.conf`、`odoo-venv/`**，不读取或泄露 `admin_passwd`。
3. **数据库破坏性操作前先说明并获确认**：禁止 `db drop`、`dropdb`、`DROP/TRUNCATE`、`git reset --hard`、对项目/核心的 `rm -rf`。高风险升级先 `make backup` 或 `make duplicate`，测试优先在 `Goody_test` 副本上跑。
4. **所有命令从 `/opt/odoo20` 执行**，使用 `odoo-venv/bin/python odoo-bin ...`，不要用系统 Python。
5. **一模块一直接子目录**：`custom/<module>/`，模块名匹配 `^[a-z][a-z0-9_]*$`，不得与 `odoo/addons` 重名。
6. **模块版本 `20.0.x.y.z`**；专有定制 `license: 'OPL-1'`；不复制 OEEL-1 企业代码。
7. **优先使用 Makefile 和脚本**。新建模块用 `scripts/new_module.py`，不要用 `odoo-bin scaffold`（其模板仍生成过时的 `ir.model.access.csv`）。

## Odoo 20 API 速查（已对照当前源码验证）

| 主题 | 正确写法 | 禁止/已移除 |
|---|---|---|
| 访问权限 | `security/ir.access.csv`，表头 `id,name,model_id,group_id/id,operation,domain` | `ir.model.access.csv`、`ir.model.access` |
| 记录限制 | `ir.access` + 空 `group_id` + `domain` | `ir.rule` |
| 列表视图 | `<list>` | `<tree>` |
| 动态属性 | `invisible="state == 'draft'"` 等表达式属性 | `attrs=`、`states=` |
| 约束 | `models.Constraint('unique(...)', 'message')` | `_sql_constraints` |
| 显示名 | `_compute_display_name()` | `name_get()` |
| 名称搜索 | `_rec_names_search = ('name', 'code')` | list |
| 控制器 | `@http.route(..., type="jsonrpc")` | `type="json"` |
| 用户/组 | `res.users.group_ids`、`res.groups.user_ids`、`privilege_id`、`implied_by_ids` | `groups_id`、`users`、`category_id` |
| 前端 | OWL `3.0.0-alpha.49`，以 `odoo/addons/web/static/src` 为准 | Owl 2 教程写法 |

其他已验证事实：

- `security/ir.access.csv` 的 `model_id` 使用技术名 `module.model`，不是 `model_xxx`。
- `operation` 是 `c/r/u/d` 的组合；`crud` 表示全部。
- `ir.access` 记录有 `group_id` 时是 permission；没有 `group_id` 且有 `domain` 时是 restriction。
- `odoo/__init__.py` 缺失是 Odoo 20 的 namespace package 设计（入口为 `odoo/init.py`），**不要补**。
- `/etc/odoo20.conf` 的 `addons_path` 指向不存在的 `/opt/odoo20/addons`，systemd 服务已禁用；开发统一使用项目内 `odoo20.conf`。

## 目录

```text
/opt/odoo20/
├── odoo/                 # 上游核心/企业源码，只读
├── odoo-venv/            # Python 虚拟环境
├── odoo20.conf           # 本地配置（含密码哈希，不提交）
├── custom/               # 企业定制模块（本工作区唯一开发目录）
├── oca/ app3/ web/       # 其他 addons 目录（第三方/历史模块）
├── scripts/              # new_module.py / check_module.py / templates
├── docs/                 # 开发规范与工作流
└── .claude/              # Claude Code 配置（权限、hooks、commands、agents、skills）
```

## 常用命令

```bash
make env                                  # 检查版本、Python、数据库、custom 模块
make run                                  # 启动 (--dev=xml)，默认 Goody
make run DB=demo                          # 指定数据库
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=base KIND=model
make install MODULE=custom_demo           # 安装
make update MODULE=custom_demo            # 升级
make test MODULE=custom_demo              # 升级并跑测试
make test-fast MODULE=custom_demo         # 不升级，直接跑测试
make validate MODULE=custom_demo          # 静态校验
make lint                                 # Ruff 检查 custom/scripts/hooks
make shell                                # Odoo shell
make i18n-export MODULE=custom_demo LANG=zh_CN
make backup                               # 备份 Goody（含 filestore）
make duplicate                            # 复制为 Goody_test 并 neutralize
```

## 开发工作流

1. **读核心/企业源码**：先在 `odoo/addons/` 找到目标模型、字段、视图 XML ID 和继承点；确认不是要复制核心逻辑。
2. **规划**：说明要扩展的模型/视图、依赖、数据变更和测试点。
3. **建骨架**：`make new-module ...`，不要用内置 scaffold。
4. **实现**：模型优先 `_inherit`；视图用 `xpath` + `<list>` + 表达式属性；安全用 `ir.access`；约束用 `models.Constraint`。
5. **校验**：`make validate MODULE=...`，修复所有 ERROR。
6. **安装/升级**：`make install` 或 `make update`；只升级目标模块，不要 `-u all`。
7. **测试**：`make test MODULE=...`；高风险改动先在 `Goody_test` 副本。
8. **翻译**：源码字符串英文，`make i18n-export ... LANG=zh_CN`。
9. **审查**：`/review-custom <module>` 或调用 `odoo-reviewer` 子代理。

## Claude Code 使用约定

- 新建模块：`/new-module <name> [depends] [extension|model]`
- 静态校验：`/check-module <name>`
- 升级：`/update-module <name> [db]`
- 测试：`/test-module <name> [db]`
- 审查：`/review-custom <name>`
- 翻译：`/i18n <name> [export|import|pot] [file.po]`
- 复杂模块开发可直接用自然语言描述，`odoo-module-development` skill 会提供工作流和检查表。
- PreToolUse hooks 会阻止修改核心/配置/venv 以及危险 shell 命令；PostToolUse hook 会检查 Python/XML/CSV 是否符合 Odoo 20。
- 项目 `.claude/settings.json` 不覆盖用户级 provider/model 配置。

## 已知注意事项

- `custom/` 为空时启动会出现 `invalid addons directory` warning，创建首个模块后消失；不要为消除警告造假模块。
- `--dev=xml` 只对 `arch_updated=False` 的视图从源码读取；Studio 修改过的视图仍以数据库为准。
- `Goody` 含 Studio 定制，改代码前先备份；避免对同一视图同时做 Studio 和 XML 定制。
- Pylance 已限制诊断范围为当前打开文件；全量索引 1,574 个模块会较慢。
- hook 是防误操作护栏，不是安全沙箱；覆盖开关见 `docs/claude-code-setup.md`。
