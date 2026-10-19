# Odoo 20 开发工作流

所有命令默认在 `/opt/odoo20` 执行，使用 `odoo-venv/bin/python`。

## 1. 环境检查

```bash
make env
```

输出包括 Odoo 版本、Python 版本、`Goody` 已安装模块数、`custom/` 下的模块列表。

手动检查：

```bash
odoo-venv/bin/python odoo-bin --version
psql -d Goody -Atc "select count(*) from ir_module_module where state='installed';"
```

## 2. 启动与调试

```bash
make run                 # Goody + --dev=xml
make run DB=demo         # 指定数据库
make run-dev             # --dev=all
```

VS Code：

- `Odoo: Run (dev=xml)`：启动并附加调试器，断点可停在 `custom/`；`justMyCode=false` 可单步进入 Odoo 框架。
- `Odoo: Run (dev=all)`：包含 Python 重载、QWeb 调试等。
- `Odoo: Test Module`：升级并运行指定模块测试。
- `Odoo: Shell`：在调试器中打开 Odoo shell。

`--dev` 模式说明：

| 模式 | 作用 |
|---|---|
| `xml` | 从源码重新读取视图，但仅对 `arch_updated=False` 的视图有效 |
| `reload` | Python 代码变更后重启服务 |
| `qweb` | QWeb 错误输出更详细 |
| `access` | 访问错误输出 traceback |
| `all` | 以上全部 |

注意：

- `--dev=xml` 不会覆盖 Studio 写入数据库的视图；Studio 定制仍以数据库为准。
- JS/SCSS 改动需要硬刷新浏览器；`--dev=xml` 不会重新打包前端资源。
- 修改 Python 后如未使用 `reload`，需要重启服务。

## 3. 新建模块

```bash
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=base KIND=extension
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=account_accountant,mail KIND=model ENTITY=approval
```

生成的 `model` 骨架包含：

- `models/<entity>.py`：模型、`company_id`、`models.Constraint`
- `security/<module>_security.xml`：`res.groups.privilege` + 用户/经理组
- `security/ir.access.csv`：Odoo 20 访问权限
- `views/<module>_views.xml`：`<list>`/`<form>`/`<search>`、action、menu
- `tests/test_<module>.py`：`TransactionCase` + `post_install`

不要使用 `odoo-bin scaffold`：Odoo 20 自带模板仍生成 `security/ir.model.access.csv`。

## 4. 安装、升级、校验

```bash
make validate MODULE=custom_demo
make install MODULE=custom_demo
make update MODULE=custom_demo
```

只升级目标模块，不要使用 `-u all`。检查数据库状态：

```bash
psql -d Goody -Atc "select name,state,latest_version from ir_module_module where name='custom_demo';"
```

预期：`installed|20.0.1.0.0`。

## 5. 测试

```bash
make test MODULE=custom_demo              # 升级 + 测试
make test-fast MODULE=custom_demo         # 不升级，直接测试
make test MODULE=custom_demo DB=Goody_test
```

底层命令：

```bash
odoo-venv/bin/python odoo-bin server -c odoo20.conf -d Goody \
  -u custom_demo --test-tags /custom_demo --stop-after-init --no-http
```

说明：

- `--test-tags /custom_demo` 会运行该模块的测试。
- `--stop-after-init` 在测试后退出；`--no-http` 避免端口冲突。
- 高风险测试先复制数据库：`make duplicate` → 在 `Goody_test` 上测试。
- 测试输出出现 `0 failed, 0 error(s)` 视为通过。

## 6. Odoo Shell

```bash
make shell
# 或
odoo-venv/bin/python odoo-bin shell -c odoo20.conf -d Goody
```

常用：

```python
self.env['ir.module.module'].search([('name', '=', 'custom_demo')])
self.env['acme.approval'].search([])
self.env.cr.rollback()  # 放弃当前事务中的修改
```

注意：shell 中的写操作会进入事务；不确定时先 `rollback()`。

## 7. i18n

```bash
# 确保语言已安装（如未安装）
odoo-venv/bin/python odoo-bin i18n loadlang -c odoo20.conf -d Goody -l zh_CN

# 导出/模板
make i18n-export MODULE=custom_demo LANG=zh_CN
make i18n-pot MODULE=custom_demo

# 导入（覆盖已有翻译）
make i18n-import MODULE=custom_demo FILE=custom/custom_demo/i18n/zh_CN.po LANG=zh_CN
```

规则：

- 模块必须已安装才能正常导出。
- 源码字符串英文，`msgstr` 写中文；不要手改 `msgid`。
- 导出后检查 `custom/<module>/i18n/zh_CN.po`。

## 8. 备份、复制、恢复

```bash
make backup                       # backups/Goody-YYYYmmdd-HHMMSS.zip，含 filestore
make duplicate                    # 复制 Goody -> Goody_test，并 neutralize
```

手动恢复（不要覆盖 `Goody`）：

```bash
odoo-venv/bin/python odoo-bin db -c odoo20.conf load Goody_restore backups/Goody-xxxx.zip -n
```

说明：

- `db dump` 默认 zip 格式并包含 filestore；只做 `pg_dump` 会丢附件。
- `make duplicate` 使用 `-n`（neutralize），避免副本发邮件。
- 恢复目标使用新库名，确认无误后再切换。
- 生产数据/主库操作前先备份。

## 9. Lint

```bash
make dev-setup      # 安装 ruff 到 odoo-venv
make lint           # 检查 custom/ scripts/ .claude/hooks/
make lint-fix       # 自动修复可修复项
```

`ruff.toml` 排除了 `odoo/`、`odoo-venv/`、`oca/`、`app3/`、`web/`、`backups/`。

## 10. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `invalid addons directory '/opt/odoo20/custom', skipped` | `custom/` 为空 | 创建首个模块后消失，不要造假模块 |
| `database "odoo" does not exist` | `psql` 默认库不存在 | 使用 `psql -d Goody` |
| 端口 8069 被占用 | 已有 Odoo 进程 | `--http-port=8070` 或停止旧进程 |
| `odoo/__init__.py` 不存在 | Odoo 20 namespace package 设计 | 不要补；入口是 `odoo/init.py` |
| systemd 启动失败 | `/etc/odoo20.conf` 的 `addons_path` 指向不存在的 `/opt/odoo20/addons` | 开发用项目 `odoo20.conf`，不要依赖该服务 |
| Studio 改动不生效 | Studio 视图存在数据库，`--dev=xml` 不覆盖 | 通过 Studio 修改，或备份后处理 |
| `make test` 报模块未安装 | `-u` 只能升级已安装模块 | 先 `make install MODULE=...` |
| `i18n export` 警告/失败 | 模块未安装 | 先安装模块 |
| Pylance 卡顿 | 全量索引 1,574 个模块 | 已设置 `openFilesOnly`；必要时关闭 `python.analysis.indexing` |
| hooks 不触发 | 工作区未信任、JSON 无效、扩展未重启 | 检查 `.claude/settings.json`、信任工作区、重启扩展 |
| `ruff: command not found` | 未安装开发工具 | `make dev-setup` |
| 命令行调试缺 debugpy | venv 未安装 debugpy | VS Code debugpy 扩展已够用；命令行调试再 `pip install debugpy` |
| `Goody` 升级很久/锁表 | 模块多或迁移重 | 只升级目标模块；先在 `Goody_test` 验证 |
| 嵌套目录模块不被发现 | addons 只扫描直接子目录 | 一模块一直接子目录：`custom/<module>/` |

## 11. 数据库安全

- 主库：`Goody`；测试副本：`Goody_test`。
- 不要对 `Goody` 执行 `db drop`、`dropdb`、`DROP/TRUNCATE`、`-u all`。
- 升级前 `make backup`；高风险改动先 `make duplicate`。
- hooks 会拦截常见危险命令，但它们是护栏，不是权限系统；关键操作仍需人工确认。
