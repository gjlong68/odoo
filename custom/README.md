# custom/ — 企业定制模块

本目录是 `/opt/odoo20` 的默认定制模块目录，已在 `odoo20.conf` 的 `addons_path` 中。

## 规则

- 一模块一直接子目录：`custom/<module>/`，不要嵌套成 `custom/team/module/`。
- 模块名匹配 `^[a-z][a-z0-9_]*$`，且不得与 `odoo/addons/` 中的核心/企业模块重名。
- 模块版本使用 `20.0.x.y.z`；专有定制 `license: 'OPL-1'`。
- 不修改 `odoo/`；通过 `_inherit`、视图 xpath、assets 扩展。
- 安全文件使用 `security/ir.access.csv`，不是 `ir.model.access.csv`。
- 视图使用 `<list>` 和表达式属性；约束使用 `models.Constraint`。

## 新建模块

```bash
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=base KIND=extension
make new-module MODULE=custom_demo TITLE="Demo" DEPENDS=account_accountant KIND=model ENTITY=approval
```

或在 Claude Code 中：

```text
/new-module custom_demo account_accountant model
```

## 验证与安装

```bash
make validate MODULE=custom_demo
make install MODULE=custom_demo
make test MODULE=custom_demo
```

## 目录示例

```text
custom/
├── README.md
├── custom_demo/
│   ├── __manifest__.py
│   ├── models/
│   ├── views/
│   ├── security/
│   │   ├── custom_demo_security.xml
│   │   └── ir.access.csv
│   └── tests/
└── custom_account_ext/
    ├── __manifest__.py
    └── views/account_move_views.xml
```

`custom/` 为空时，Odoo 启动会记录 `invalid addons directory` warning；创建首个模块后消失，不需要为此造假模块。
