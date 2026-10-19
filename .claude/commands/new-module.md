---
description: 在 custom/ 下创建符合 Odoo 20 规范的模块骨架
argument-hint: <module_name> [depends] [extension|model]
---

在当前 Odoo 20 工作区创建模块。用户参数：`$ARGUMENTS`

步骤：

1. 解析参数：`$1` 为模块名；`$2` 为逗号分隔的依赖（默认 `base`）；`$3` 为类型 `extension` 或 `model`（默认 `extension`）。
2. 先检查 `custom/$1` 是否已存在，以及 `$1` 是否与 `odoo/addons` 中的核心/企业模块冲突。
3. 运行：
   `odoo-venv/bin/python scripts/new_module.py --name "$1" --depends "${2:-base}" --kind "${3:-extension}" --dest custom`
4. **不要**运行 `odoo-bin scaffold`：Odoo 20 自带模板仍会生成过时的 `security/ir.model.access.csv`。
5. 列出生成的文件，汇报模块路径、manifest 版本、安全文件类型，以及下一步命令（`make validate`、`make install`、`make test`）。
6. 参数不足或模块名不合法时先询问用户，不要猜测。
