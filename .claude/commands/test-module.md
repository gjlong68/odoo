---
description: 升级并运行指定 Odoo 20 模块的测试
argument-hint: <module_name> [database]
---

运行模块 `$1` 的测试，数据库默认 `Goody`；如果提供了 `$2`，使用 `$2`。

步骤：

1. 如果是高风险改动，先建议 `make duplicate DB=<database>`，在 `<database>_test` 上测试。
2. 执行 `make test MODULE=$1 DB=<database>`。
3. 解析输出：`0 failed, 0 error(s)` 为通过；列出失败测试的类名、方法名和 traceback 关键行。
4. 不要为了通过测试而删除断言；先修复实现或测试数据。
5. 汇报测试数量、耗时、失败原因和建议修复。
6. 如果只是快速验证已安装模块，可用 `make test-fast MODULE=$1 DB=<database>`。
