---
description: 静态校验 Odoo 20 模块的 manifest、Python、XML、安全 CSV 和结构
argument-hint: <module_name>
---

对模块 `$1` 运行静态校验：

1. 执行 `odoo-venv/bin/python scripts/check_module.py "$1"`。
2. 汇总 ERROR/WARN；对每个 ERROR 给出 `文件:行号` 和修复建议。
3. 修复后重新运行，直到 0 error。不要为了让检查通过而删除测试或安全规则。
4. 如果用户未提供模块名，先运行 `make list-modules`，列出结果后询问。

重点检查项：

- manifest 版本必须是 `20.0.x.y.z`，license 合法。
- 不得出现 `security/ir.model.access.csv`、`<tree>`、`attrs=`、`states=`、`ir.rule`、`_sql_constraints`、`name_get`、`type="json"`。
- `security/ir.access.csv` 表头必须是 `id,name,model_id,group_id/id,operation,domain`。
