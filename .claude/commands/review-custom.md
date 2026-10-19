---
description: 只读审查 custom/ 下的 Odoo 20 定制模块
argument-hint: <module_name>
---

使用 `odoo-reviewer` 子代理审查模块 `$1`。

交给子代理的提示中说明：

- 模块路径：`custom/$1`（如果不存在，先查找实际路径）。
- 审查范围：manifest、models、views、security、controllers、tests、migrations。
- 重点：Odoo 20 API（`ir.access`、`<list>`、表达式属性、`models.Constraint`、`_compute_display_name`、`type="jsonrpc"`）、继承是否正确、安全、性能、升级兼容性。
- 输出格式：`severity | file:line | issue | fix`。

主会话汇总后按严重程度排序。**不要修改文件**，除非用户明确要求修复。
