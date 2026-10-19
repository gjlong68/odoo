---
name: odoo-module-development
description: 创建、扩展、修改或审查 Odoo 20 企业定制模块时使用。覆盖 manifest、ORM、视图继承、ir.access 安全、OWL 3、测试、i18n、升级迁移。触发词：Odoo 模块、定制模块、二次开发、继承视图、加字段、升级模块、Odoo addon。
---

# Odoo 20 模块开发

## 适用场景

- 在 `/opt/odoo20/custom/` 下新建企业定制模块。
- 通过 `_inherit`、`_inherits` 或视图 xpath 扩展 Odoo Enterprise 模块。
- 为已有定制模块加字段、视图、权限、控制器、测试或迁移脚本。
- 审查定制模块是否符合 Odoo 20 API 和项目规范。

## 工作流

1. **先读核心/企业源码**：确认要扩展的模型、字段、视图 XML ID 和继承点。核心与企业代码都在 `odoo/addons/`，只读。
2. **确认不修改核心**：所有代码写入 `custom/<module>/`。
3. **创建骨架**：`make new-module MODULE=<name> [DEPENDS=account,mail] [KIND=extension|model]`。不要用 `odoo-bin scaffold`。
4. **实现**：
   - 模型：`_inherit` 扩展，新增字段用 `x_` 前缀（或项目约定前缀）；约束用 `models.Constraint`。
   - 视图：`<field name="inherit_id" ref="module.view_xmlid"/>` + `<xpath>`；列表用 `<list>`；动态属性用表达式。
   - 安全：`security/ir.access.csv`；需要记录限制时用 `ir.access` 记录 + `domain`。
   - 测试：`@tagged('post_install', '-at_install')` + `TransactionCase`/`HttpCase`。
5. **静态校验**：`make validate MODULE=<name>`，修复所有 ERROR。
6. **安装/升级**：`make install MODULE=<name>` 或 `make update MODULE=<name>`。
7. **测试**：`make test MODULE=<name>`；高风险改动先在 `Goody_test` 副本上跑。
8. **翻译**：源码字符串英文，`make i18n-export MODULE=<name> LANG=zh_CN`。
9. **审查**：`/review-custom <name>` 或调用 `odoo-reviewer` 子代理。

## 硬规则

- 不修改 `odoo/`；不修改 `odoo20.conf`、`odoo-venv/`。
- 不复制 OEEL-1 企业代码到定制模块；定制模块 license 默认 `OPL-1`。
- Odoo 20 已移除：`ir.model.access`、`ir.rule`、`<tree>`、`attrs`/`states`、`_sql_constraints`、`name_get`、`type="json"`。
- 使用：`security/ir.access.csv`、`<list>`、表达式属性、`models.Constraint`、`_compute_display_name`、`type="jsonrpc"`、`res.users.group_ids`/`res.groups.user_ids`。
- 前端是 OWL 3（当前 `3.0.0-alpha.49`）；以 `odoo/addons/web/static/src` 源码为准，不要照搬 Owl 2 教程。
- 数据库破坏性操作前先备份；不要对 `Goody` 执行 `-u all`、`db drop`、`DROP/TRUNCATE`。
- 模块版本 `20.0.x.y.z`；每次发布递增。

## 参考

- `docs/odoo20-development-standards.md`：完整开发规范。
- `docs/enterprise-customization.md`：企业模块二次开发规则。
- `references/checklist.md`：实现/审查检查表。
- `scripts/check_module.py`：静态校验脚本。
