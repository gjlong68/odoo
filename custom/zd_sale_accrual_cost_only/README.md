# Sales Accrual Cost Only（销售应计只记成本）

Odoo 20 定制模块：销售发货库存估值应计只生成成本分录，不生成收入分录。

## 背景

Odoo 20「库存估值」报表的 **Generate Entries / 生成分录** 按钮，以及销售订单行上的
**Create Accrual Entries / 创建应计分录**，都会调用 `account.accrued.orders.wizard`。
对“已发货未开票”的实时估值（real_time）可库存产品，核心默认生成两组分录：

| 组 | 借方 | 贷方 |
|---|---|---|
| 收入组 | 1406.01 已发货未开票（按售价） | 6001.01 主营业务收入 |
| 成本组 | 6401.01 主营业务成本（按成本） | 1405.01 产品(自产) |

本模块删除收入组，把成本组改为纯资产负债表重分类：

| 场景 | 分录 |
|---|---|
| 已发货未开票 | **借：1406.01 已发货未开票 / 贷：1405.01 产品(自产)** |
| 票已开货未发（反向） | **借：1405.01 产品(自产) / 贷：2205.01 已开票未发货** |
| 冲销凭证 | 镜像上述两行 |

冲销凭证仍由应计向导的 `_reverse_moves()` 自动生成，保持 `auto_post='at_date'` 原生行为。

## 范围

- 所有销售行：销售应计不再生成收入分录。
- real_time 且 `is_storable` 的销售行生成上述成本分录。
- periodic 存货、服务行没有成本侧，因此不再生成应计。
- 销售应计禁用手动金额（`amount`），输入即报错。
- 采购应计、销售发票、标准 COGS 分录不受影响。
- 公司间采购退货的镜像销售行不生成销售应计：该成本已由采购侧的
  `bill_to_receive` / `billed_not_received` 应计处理，避免重复贷记库存科目。

## 公司间采购退货

公司间采购退货的出库移动会同时带 `purchase_line_id` 和 `sale_line_id`，
目标库位为全局 `Inter-company transit`。采购侧应计：

> 借：1401.01 票到货未到 / 贷：1405.01 产品(自产)

镜像销售行若再生成 `invoices_to_issue` 应计，会重复贷记 1405.01。
本模块在销售应计候选（`_get_accrual_line_ids`）和应计向导中排除这类行；
直接对应计镜像行执行时会给出手工金额/镜像行的明确报错。

同时，`sale_stock` 的库存校验会把“发往中转库位的出库”误判为销售出库，
在关联销售单上自动创建零数量销售行并写回 `sale_line_id`，导致退货单
`WH/OUT/xxxxx` 出现在销售单的交货单列表里。本模块：

- 在 `stock.move._action_synch_order()` 中跳过公司间采购退货移动；
- 在 `sale.order.line.create()` 中拒绝为这类移动创建销售行；
- 升级迁移会清理历史数据：清空退货移动的 `sale_line_id`、移除退货单与
  销售单的关联、删除仅由该移动产生的零数量销售行。

## 公司间红字发票 Storno

公司间规则自动生成的红字发票（`in_refund` / `out_refund`，`auto_generated=True`）
在启用 Storno 的公司下，税额行可能仍以“正数反方向”列示。例如：

```text
借：1405.01 产品(自产)  -7,500
贷：2221.01.02 进项税额    975
贷：2202.02 应付账款-集团 -8,475
```

本模块在过账后把税额行改为 Storno 列示：

```text
借：1405.01 产品(自产)  -7,500
借：2221.01.02 进项税额   -975
贷：2202.02 应付账款-集团 -8,475
```

只处理 `auto_generated` 且 `is_refund()` 的凭证，且仅在 `company.account_storno`
启用时生效；手工红字发票和未启用 Storno 的公司不受影响。

## 科目配置

模块不硬编码科目，按 Odoo 原生字段解析：

- 库存科目：`product.category.property_stock_valuation_account_id`
  （为空时回退公司 `account_stock_valuation_id`）
- 已发货未开票：`product.category.property_account_invoices_to_issue_id`
  （为空时回退公司 `account_invoices_to_issue_id`）
- 已开票未发货：`product.category.property_account_invoiced_not_delivered_id`
  （为空时回退公司 `account_invoiced_not_delivered_id`）

Goody 公司 1 的当前配置：

- 产成品类别库存科目：1405.01 产品(自产)
- 公司默认已发货未开票：1406.01 已发货未开票
- 公司默认已开票未发货：2205.01 已开票未发货

## 安装与测试

```bash
make install MODULE=zd_sale_accrual_cost_only
make test MODULE=zd_sale_accrual_cost_only DB=Goody_test
```

## 已知限制

- 只影响安装后新生成的应计；历史已过账应计及冲销不会自动调整。
- 科目未配置时该行会被跳过（与核心一致），上线前确认公司/产品类别已配置上述科目。
- 公司间自动镜像销售行、dropship 等特殊场景仍按销售侧统一处理；如有单独规则需另行过滤。
