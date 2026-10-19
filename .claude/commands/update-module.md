---
description: 升级指定 Odoo 20 模块并验证数据库状态
argument-hint: <module_name> [database]
---

升级模块 `$1`，数据库默认 `Goody`；如果提供了 `$2`，使用 `$2`。

步骤：

1. 确认模块目录在 `custom/$1`，先运行 `odoo-venv/bin/python scripts/check_module.py "$1"`。
2. 执行 `make update MODULE=$1 DB=<database>`。
3. 检查输出中的 ERROR/WARNING；升级完成后运行：
   `psql -d <database> -Atc "select name,state,latest_version from ir_module_module where name='$1';"`
4. 汇报 state、版本号、错误摘要。
5. 不要使用 `-u all`。升级失败时先读日志定位，不要直接改核心或删库。
6. 如果是高风险改动或主库 `Goody`，建议先执行 `make backup`，或在 `Goody_test` 副本上验证。
