# Odoo 20 开发规范

本文档面向 `/opt/odoo20` 的企业定制模块开发。所有规则以当前 Odoo 20.0 Enterprise 源码为准；如与旧版 Odoo 教程冲突，以 `odoo/addons/` 中的实际写法为准。

## 1. 模块布局

```text
custom/<module>/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <entity>.py
├── views/
│   └── <module>_views.xml
├── security/
│   ├── <module>_security.xml
│   └── ir.access.csv
├── controllers/
│   └── __init__.py
├── static/src/
├── tests/
│   ├── __init__.py
│   └── test_<module>.py
├── i18n/
│   └── zh_CN.po
└── migrations/
    └── <version>/
        ├── pre-migrate.py
        └── post-migrate.py
```

规则：

- 一模块一直接子目录，模块名 `^[a-z][a-z0-9_]*$`。
- 模块名不要与 `odoo/addons/` 中的核心/企业模块重名。
- 不复制核心模块的目录结构；只创建实际需要的子目录。
- 前端资源统一放在 `static/src/`，通过 manifest 的 `assets` 注册。

## 2. Manifest

```python
{
    'name': 'ACME Account Extension',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Company-specific accounting customizations',
    'author': 'ACME',
    'website': 'https://example.com',
    'license': 'OPL-1',
    'depends': ['account_accountant', 'mail'],
    'data': [
        'security/acme_account_security.xml',
        'security/ir.access.csv',
        'views/account_move_views.xml',
        'report/account_move_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'acme_account/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
```

规则：

- `version` 必须是 `20.0.x.y.z`；每次发布递增。
- `license`：公司专有定制使用 `OPL-1`；不要复制 OEEL-1 企业代码。
- `depends` 明确列出实际使用的模块；不要依赖自动安装的偶然结果。
- `data` 顺序：security → data → views → reports。
- `assets` 使用 Odoo 20 的 bundle 名称（如 `web.assets_backend`、`web.assets_frontend`）。
- `application` 仅在模块提供独立应用菜单时设为 `True`。

## 3. 模型与 ORM

### 3.1 扩展现有模型

优先使用 `_inherit`，不要复制原模型定义：

```python
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_acme_approved_by_id = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False,
    )
    x_acme_approval_date = fields.Datetime(
        string='Approval Date', readonly=True, copy=False,
    )

    def action_acme_approve(self):
        self.write({
            'x_acme_approved_by_id': self.env.user.id,
            'x_acme_approval_date': fields.Datetime.now(),
        })
```

- 自定义字段使用项目统一前缀（常用 `x_`），避免与未来核心字段冲突。
- 覆盖核心方法时先调用 `super()`，并保持原方法契约。
- 不要用 monkey patch 修改核心行为；确需修改前端行为时使用官方 patch 机制，并在代码中注释原因。

### 3.2 新建模型

```python
from odoo import api, fields, models


class AcmeApproval(models.Model):
    _name = 'acme.approval'
    _description = 'ACME Approval'
    _order = 'create_date desc'
    _rec_names_search = ('name', 'reference')

    name = fields.Char(required=True, index=True)
    reference = fields.Char(index=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('approved', 'Approved')],
        default='draft',
        required=True,
    )

    _name_company_uniq = models.Constraint(
        'unique(name, company_id)',
        'The name must be unique per company.',
    )

    @api.depends('name', 'reference')
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f'{record.name} ({record.reference})'
                if record.reference else record.name
            )
```

规则：

- `_description` 必填。
- `_order` 明确排序，避免依赖数据库默认顺序。
- 常用搜索字段加 `index=True`。
- 多公司模型使用 `company_id`；关系字段必要时 `check_company=True`。
- 约束使用 `models.Constraint('unique(...)', 'message')`；**不要**使用 `_sql_constraints`。
- 显示名使用 `_compute_display_name()`；**不要**使用 `name_get()`。
- `_rec_names_search` 必须是 tuple，例如 `('name', 'code')`。
- 不在模块代码中调用 `cr.commit()`；事务由 Odoo 管理。
- `sudo()` 只用于明确需要绕过权限的窄场景，并注释原因。

## 4. 视图

### 4.1 继承视图

```xml
<record id="view_move_form_inherit_acme" model="ir.ui.view">
    <field name="name">account.move.form.inherit.acme</field>
    <field name="model">account.move</field>
    <field name="inherit_id" ref="account.view_move_form"/>
    <field name="arch" type="xml">
        <xpath expr="//sheet" position="inside">
            <group string="ACME Approval" invisible="state != 'posted'">
                <field name="x_acme_approved_by_id" readonly="1"/>
                <field name="x_acme_approval_date" readonly="1"/>
            </group>
        </xpath>
    </field>
</record>
```

规则：

- 先读上游视图，确认 `inherit_id` 和 xpath 锚点存在。
- 优先使用稳定的锚点（如 `//sheet`、`//field[@name='partner_id']`），避免依赖易变的序号。
- 多个定制模块改同一视图时，使用不同的 xpath 锚点，减少冲突。
- 视图 ID 使用 `<module>_<purpose>` 命名，避免重复。

### 4.2 列表 / 表单 / 搜索

```xml
<record id="view_acme_approval_list" model="ir.ui.view">
    <field name="name">acme.approval.list</field>
    <field name="model">acme.approval</field>
    <field name="arch" type="xml">
        <list>
            <field name="name"/>
            <field name="reference"/>
            <field name="company_id" groups="base.group_multi_company"/>
            <field name="state"/>
        </list>
    </field>
</record>
```

- 列表使用 `<list>`；**不要**使用 `<tree>`。
- 动态属性使用表达式：`invisible="state != 'posted'"`、`readonly="..."`、`required="..."`。
- **不要**使用 `attrs=` 或 `states=`。
- 多公司字段加 `groups="base.group_multi_company"`。
- 搜索视图使用 `<filter>` + `domain`，不要写死 Python 逻辑。

## 5. 安全

Odoo 20 用 `ir.access` 统一替代 `ir.model.access` 和 `ir.rule`。

### 5.1 访问权限 CSV

`security/ir.access.csv`：

```csv
id,name,model_id,group_id/id,operation,domain
access_acme_approval_user,acme.approval user,acme.approval,acme.group_acme_user,crud,
access_acme_approval_portal,acme.approval portal,acme.approval,base.group_portal,r,
```

规则：

- 文件必须是 `security/ir.access.csv`，**不要**创建 `ir.model.access.csv`。
- 表头固定：`id,name,model_id,group_id/id,operation,domain`。
- `model_id` 使用技术名 `module.model`（例如 `acme.approval`），不是 `model_acme_approval`。
- `operation` 是 `c/r/u/d` 的组合；`crud` 表示全部。按最小权限原则选择。
- 含逗号的 `domain` 必须用双引号包裹。
- 每个新模型至少有 user/manager 访问规则。

### 5.2 分组与权限范围

```xml
<record id="privilege_acme" model="res.groups.privilege">
    <field name="name">ACME</field>
    <field name="sequence">100</field>
</record>

<record id="group_acme_user" model="res.groups">
    <field name="name">ACME / User</field>
    <field name="privilege_id" ref="privilege_acme"/>
</record>

<record id="group_acme_manager" model="res.groups">
    <field name="name">ACME / Manager</field>
    <field name="privilege_id" ref="privilege_acme"/>
    <field name="implied_ids" eval="[(4, ref('group_acme_user'))]"/>
</record>
```

- Odoo 20 使用 `res.groups.privilege` 组织权限范围。
- 用户字段是 `res.users.group_ids`；组上的用户字段是 `res.groups.user_ids`。
- 不要把旧版的 `groups_id`、`users`、`res.groups.category_id` 写法带进来。

### 5.3 记录限制

```xml
<record id="access_acme_approval_company" model="ir.access">
    <field name="name">ACME Approval: company restriction</field>
    <field name="model_id" ref="model_acme_approval"/>
    <field name="operation">crud</field>
    <field name="domain">[('company_id', 'in', company_ids)]</field>
</record>
```

- `ir.access` 记录没有 `group_id`、但有 `domain` 时是 restriction。
- 有 `group_id` 时是 permission；可以同时带 `domain` 限制该组的可见范围（参考 `hr_timesheet`、`project` 的企业写法）。
- 可用上下文：`user`、`time`、`company_id`、`company_ids`。
- **不要**使用 `ir.rule`；Odoo 20 已没有该模型。

## 6. 控制器 / HTTP

```python
from odoo import http
from odoo.http import request


class AcmeApprovalController(http.Controller):
    @http.route('/acme/approvals', type='jsonrpc', auth='user')
    def list_approvals(self, **kwargs):
        records = request.env['acme.approval'].search([])
        return [{'id': record.id, 'name': record.name} for record in records]

    @http.route('/acme/approvals/<int:approval_id>', type='http', auth='user')
    def approval_page(self, approval_id, **kwargs):
        record = request.env['acme.approval'].browse(approval_id)
        return request.render('acme_account.approval_page', {'record': record})
```

规则：

- JSON-RPC 使用 `type='jsonrpc'`；**不要**使用 `type='json'`。
- `auth` 按最小权限选择：`user`、`portal`、`public`。
- HTTP POST 保持 CSRF 保护；不要随意设置 `csrf=False`。
- 控制器只做参数校验和调用模型方法，业务逻辑放模型层。
- 公开路由要做输入校验和速率/权限评估。

## 7. 前端 OWL 3

Odoo 20 使用 OWL `3.0.0-alpha.49`。Owl 2 教程中的 `useState`、静态 props 等写法不一定适用。

规则：

- 以 `odoo/addons/web/static/src` 和 `odoo/addons/documents/static/src` 的现有组件为准。
- 组件放在 `static/src/`，通过 manifest 的 `assets` 注册到对应 bundle。
- 使用 Odoo 的 `registry` 注册字段、视图、服务等扩展点。
- 修改现有组件行为时使用官方 patch 工具，不要直接改 `web` 源码。
- 前端资源改动后需要硬刷新浏览器；`--dev=xml` 不会重新加载已打包的 JS/SCSS。

## 8. 测试

```python
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAcmeApproval(TransactionCase):
    def test_create(self):
        record = self.env['acme.approval'].create({'name': 'A'})
        self.assertEqual(record.name, 'A')
```

唯一约束测试：

```python
from psycopg2 import IntegrityError
from odoo.tools import mute_logger

with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
    self.env['acme.approval'].create({'name': 'A'})
```

控制器测试使用 `HttpCase`：

```python
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAcmeController(HttpCase):
    def test_route(self):
        response = self.url_open('/acme/approvals')
        self.assertEqual(response.status_code, 200)
```

规则：

- 测试类继承 `TransactionCase`（模型）或 `HttpCase`（HTTP）。
- 使用 `@tagged('post_install', '-at_install')`，避免在模块安装中途执行。
- 运行：`make test MODULE=<module>`（升级 + 测试）。
- 测试数据不要依赖 `Goody` 主库的偶然数据。
- 高风险测试先在 `Goody_test` 副本上跑。

## 9. i18n

- 源码字符串保持英文；中文翻译写入 `i18n/zh_CN.po`。
- 运行时异常/提示使用 `self.env._('...')`，例如：

```python
from odoo.exceptions import UserError

raise UserError(self.env._('The approval is already completed.'))
```

导出/导入：

```bash
make i18n-export MODULE=acme_account LANG=zh_CN
make i18n-pot MODULE=acme_account
make i18n-import MODULE=acme_account FILE=custom/acme_account/i18n/zh_CN.po LANG=zh_CN
```

规则：

- 模块必须已安装到目标数据库，`i18n export` 才能正常导出。
- 不要手改 `msgid`；只改 `msgstr`。
- 代码稳定后再导出，避免 PO 行号频繁变化。

## 10. 性能

- 避免在循环中 `search`/`browse`；先批量查询，再用 `mapped`、`filtered`、字典索引。
- 使用 `search_count` 获取数量，不要 `len(search(...))`。
- 常用过滤/排序字段加 `index=True`。
- 关系字段注意 `prefetch`；大量记录时使用 `with_context(prefetch_fields=False)` 或分批处理。
- 聚合使用 ORM 的分组 API，不要在 Python 中拉全量数据。
- `sudo()` 范围尽量小；不要用它掩盖权限问题。
- 大表结构变更评估锁表时间；必要时用迁移脚本分批处理。

## 11. 升级与迁移

版本号递增示例：`20.0.1.0.0` → `20.0.1.1.0`。

迁移脚本目录：

```text
migrations/
└── 1.1/
    ├── pre-migrate.py
    └── post-migrate.py
```

`1.1` 对应模块版本 `20.0.1.1.0`（去掉 series），也可以写完整 `20.0.1.1`。

```python
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # 示例：为历史数据补默认值；使用 env[...] 而不是直接拼 SQL
    env['acme.approval'].search([('reference', '=', False)]).write({'reference': '/'})
```

规则：

- `pre-migrate.py` 在模块加载前执行，`post-migrate.py` 在加载后执行。
- 迁移脚本必须幂等，考虑重复执行和空数据。
- 升级前备份：`make backup`。
- 高风险升级先在 `Goody_test` 副本验证：`make duplicate`。
- 不要对 `Goody` 执行 `-u all`；只升级目标模块。

## 12. 日志与异常

```python
import logging

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
```

规则：

- 模块代码不要使用 `print`。
- 预期内的用户错误用 `UserError`；数据校验用 `ValidationError`；消息用 `self.env._()` 包装。
- 意外异常用 `_logger.exception(...)` 记录，再按需抛出。
- 不要捕获裸 `Exception` 后静默吞掉。
- 不要在日志中输出密码、token、完整 SQL 参数。

## 13. 代码质量与 Git

```bash
make validate MODULE=<module>
make lint
make test MODULE=<module>
```

规则：

- `ruff.toml` 只检查 `custom/`、`scripts/`、`.claude/hooks/`；不要手动对 `odoo/` 跑格式化。
- 不要为了让 lint 通过而无理由添加 `# noqa`。
- 提交信息建议：`feat(<module>): ...`、`fix(<module>): ...`、`chore(<module>): ...`。
- 涉及数据结构变更时，同时提交版本递增和迁移脚本。
- 不提交 `odoo20.conf`、`backups/`、`__pycache__/`。
