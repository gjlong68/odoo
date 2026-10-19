# Odoo 20 定制模块检查表

## Manifest

- [ ] `name`、`version`（`20.0.x.y.z`）、`depends`、`data` 完整。
- [ ] `license` 为 `OPL-1`（专有定制）或其他合法值。
- [ ] `data` 顺序：security → data → views → reports。
- [ ] 引用的每个文件都存在。
- [ ] 没有把 `odoo/addons` 的核心模块名当作自定义模块名。

## 模型

- [ ] 扩展用 `_inherit`，不要复制原模型定义。
- [ ] 新模型 `_name = '<module>.<entity>'`，`_description` 必填。
- [ ] 新字段有合理 `string`、`index`、`required`、`default`、`help`。
- [ ] 多公司字段使用 `company_id`，必要时 `check_company=True`。
- [ ] 约束用 `models.Constraint('unique(...)', 'message')`，类属性名唯一。
- [ ] 显示名用 `_compute_display_name`，不用 `name_get`。
- [ ] `_rec_names_search` 是 tuple。
- [ ] 不在模块代码中 `cr.commit()`。
- [ ] 计算字段有正确 `@api.depends`；跨公司计算注意 `@api.depends_context('company')`。

## 视图

- [ ] 继承视图有 `inherit_id`，xpath 精确匹配上游结构。
- [ ] 列表用 `<list>`，不用 `<tree>`。
- [ ] 动态属性用 `invisible="..."`、`readonly="..."`、`required="..."`，不用 `attrs`/`states`。
- [ ] 新增字段在视图中有 `name`，必要时 `groups`、`optional`。
- [ ] 菜单/动作 XML ID 不重复，`sequence` 合理。
- [ ] 前端资源放在 `assets` 对应 bundle（`web.assets_backend` 等）。

## 安全

- [ ] 文件是 `security/ir.access.csv`，不是 `ir.model.access.csv`。
- [ ] 表头 `id,name,model_id,group_id/id,operation,domain`。
- [ ] 每个新模型至少有 user/manager 访问规则。
- [ ] `operation` 只由 `c/r/u/d` 组成；最小权限。
- [ ] 记录限制用 `ir.access` + 空 `group_id` + `domain`，不用 `ir.rule`。
- [ ] `sudo()` 只用于明确需要绕过权限的窄场景，并写注释。
- [ ] 不拼接 SQL；必须用 SQL 时使用参数化查询。

## 控制器 / 前端

- [ ] `@http.route(..., type="jsonrpc")`，不用 `type="json"`。
- [ ] `auth` 最小化（`user`/`portal`/`public` 按需）。
- [ ] CSRF 处理正确；不关闭 CSRF 除非有明确理由。
- [ ] OWL 组件遵循 Odoo 20 `web` 源码的 API（Owl 3），不照搬 Owl 2。

## 测试 / i18n / 升级

- [ ] 测试使用 `@tagged('post_install', '-at_install')`。
- [ ] 覆盖创建、约束、权限、关键计算/动作。
- [ ] 测试数据不依赖 `Goody` 主库的偶然数据。
- [ ] 源码字符串英文；`i18n/zh_CN.po` 通过 export 生成。
- [ ] 版本递增；数据结构变更提供 `migrations/<version>/pre|post-*.py`。
- [ ] 升级前备份；高风险改动先在 `Goody_test` 副本验证。
