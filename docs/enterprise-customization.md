# Odoo 20 企业模块二次开发规则

## 1. 代码布局

Odoo 20 Enterprise 的社区与企业代码合并放在：

```text
/opt/odoo20/odoo/addons/
```

没有单独的 `enterprise/` 目录。企业模块通过 manifest 的 `license: 'OEEL-1'` 标识，例如：

- `account_accountant`
- `documents`
- `web_enterprise`
- `web_studio`
- `mail_enterprise`
- `ai_documents`

查看某个模块是否为企业模块：

```bash
grep -n "license" odoo/addons/account_accountant/__manifest__.py
```

## 2. 只读原则

`odoo/addons/` 是上游源码，**任何情况下都不要修改**：

- 不直接改企业模块的 Python/XML/JS/SCSS。
- 不复制企业模块到 `custom/` 后改。
- 不通过 monkey patch 在运行时替换企业模块的核心方法。
- 升级 Odoo 时，上游文件会被覆盖，任何直接修改都会丢失并造成不可追踪的差异。

所有定制放在 `custom/<module>/`，通过官方扩展点实现：

| 需求 | 扩展方式 |
|---|---|
| 给现有模型加字段/方法 | `_inherit = 'account.move'` |
| 修改现有视图 | `inherit_id` + `<xpath>` |
| 增加列表/表单按钮 | 继承视图 + `type="object"` 方法 |
| 修改前端行为 | 官方 patch 工具 + assets |
| 新增报表 | `ir.actions.report` + QWeb 模板 |
| 新增定时任务 | `ir.cron` 数据 |
| 新增邮件模板 | `mail.template` 数据 |
| 新增权限组 | `res.groups.privilege` + `res.groups` |

## 3. 依赖选择

- `depends` 明确列出实际使用的企业模块，例如：

```python
'depends': ['account_accountant', 'mail'],
```

- 不要依赖“安装后自动带上”的模块；升级或部署时可能缺失。
- 依赖企业模块意味着该定制模块只能在 Enterprise 环境使用；在 manifest 或 README 中写明。
- 避免依赖 `web_studio` 的内部实现；Studio 是数据库定制工具，不是稳定的 API。
- 如果定制只扩展社区模块，优先依赖社区模块，减少 Enterprise 耦合。

## 4. 继承企业视图

企业视图经常变化。继承时：

1. 先读上游视图 XML，确认 `inherit_id` 和锚点。
2. 优先使用稳定的锚点（`//sheet`、`//field[@name='...']`、`//button[@name='...']`）。
3. 避免 `position="replace"` 大段替换；优先 `inside`/`after`/`before`。
4. 不要用序号 xpath（如 `//field[3]`），上游加字段就会错位。
5. 多个定制模块改同一视图时，使用不同的唯一锚点，降低冲突。

示例：

```xml
<record id="view_move_form_inherit_acme" model="ir.ui.view">
    <field name="name">account.move.form.inherit.acme</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_move_form"/>
    <field name="arch" type="xml">
        <xpath expr="//sheet" position="inside">
            <group string="ACME Approval" invisible="state != 'posted'">
                <field name="x_acme_approved_by_id" readonly="1"/>
            </group>
        </xpath>
    </field>
</record>
```

## 5. 企业模块常见扩展场景

### 5.1 会计（`account_accountant`）

- 扩展 `account.move`、`account.move.line`、`account.payment`。
- 新字段加 `x_` 前缀；涉及公司隔离时加 `company_id` 并考虑 `check_company=True`。
- 不要覆盖 `action_post` 的核心逻辑；用 `super()` 并在前后插入定制。
- 报表定制优先用 `account.report` 数据，不要改企业报表引擎。

### 5.2 文档（`documents`）

- 扩展 `documents.document` 的字段/权限。
- 注意文件夹、workspace、access token 的既有安全模型；不要用宽泛 `sudo()` 绕过。
- 前端扩展使用 `documents` 现有组件和 registry，不要直接改 `documents/static/src`。

### 5.3 Studio（`web_studio`）

- Studio 定制保存在数据库中（`studio_customization` 模块、视图/字段记录），不在源码里。
- `--dev=xml` 不会覆盖 Studio 修改过的视图。
- 避免对同一视图/字段同时做 Studio 和 XML 定制；冲突时以数据库状态为准。
- 做 Studio 定制前备份 `Goody`；导出/记录 Studio 改动，便于迁移。

### 5.4 审批 / 工作流

- 用 `state` 字段 + 按钮方法实现审批流，不要在视图里写业务逻辑。
- 状态变更用 `write`/方法封装，并加权限检查。
- 记录审批人、审批时间，便于审计。
- 需要多级审批时，新建 `acme.approval` 模型，而不是在 `account.move` 上堆字段。

## 6. License 与代码复用

- 公司专有定制模块：`license: 'OPL-1'`。
- 不要复制 `OEEL-1` 企业代码到定制模块；即使是内部使用，也会造成许可证和升级维护问题。
- 需要复用企业逻辑时，通过继承、`super()`、公开方法/模型调用，而不是复制源码。
- 对外分发定制模块前，确认依赖模块的许可证和客户授权。

## 7. 升级兼容性

Odoo 升级或企业模块更新时：

1. 先在 `Goody_test` 副本上验证：`make duplicate`。
2. 运行目标模块测试：`make test MODULE=<module> DB=Goody_test`。
3. 检查所有继承视图的 xpath 是否仍能匹配。
4. 检查企业模型字段/方法是否改名或移除（以当前源码为准）。
5. 数据结构变更时递增模块版本并提供迁移脚本。
6. 更新后再部署到主库，部署前 `make backup`。

## 8. 前端扩展

- 企业前端组件（如 `documents`、`account` 的 OWL 组件）通过官方 registry/patch 扩展。
- 不直接修改 `odoo/addons/*/static/src`。
- 资源通过 manifest 的 `assets` 注册到正确 bundle。
- Odoo 20 使用 OWL 3；以当前企业模块源码为准，不要照搬 Owl 2 教程。
- 前端改动后硬刷新浏览器；必要时用 `--dev=all`。

## 9. 安全

- 新模型必须提供 `security/ir.access.csv`。
- 复用企业模块的组时，确认组的语义和权限范围；不要假设组名永久不变。
- 记录限制用 `ir.access` + `domain`；不要用 `ir.rule`（Odoo 20 已移除）。
- `sudo()` 只用于明确的系统级操作，并注释原因。
- 公开控制器/路由做输入校验和权限检查。
- 不在日志、异常消息、前端中暴露敏感字段。

## 10. 审查清单

- [ ] 没有修改 `odoo/addons/`。
- [ ] 依赖明确，包含实际使用的企业模块。
- [ ] 继承视图的 xpath 锚点稳定，未大段 replace。
- [ ] 新字段有 `x_` 前缀，避免与核心/企业字段冲突。
- [ ] 使用 Odoo 20 API（`ir.access`、`<list>`、表达式属性、`models.Constraint`、`jsonrpc`）。
- [ ] 安全规则覆盖所有新模型，权限最小化。
- [ ] 没有复制 OEEL-1 代码；license 为 `OPL-1`。
- [ ] 测试在 `Goody_test` 副本上通过。
- [ ] 版本递增，迁移脚本齐全。
- [ ] Studio 定制与代码定制没有冲突。
