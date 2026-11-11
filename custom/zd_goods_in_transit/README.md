# Goods in Transit（发出商品）

Odoo 20 企业版定制模块：为 `real_time`（永续/开票时结转）估值的销售订单交货建立“发出商品”中转，并在开票时把 COGS 贷方从库存商品改为发出商品。

## 业务分录

| 环节 | 分录 |
| --- | --- |
| 销售订单交货 | 借：发出商品 / 贷：库存商品 |
| 客户发票过账 | 借：销售成本 / 贷：发出商品（收入分录不变） |
| 客户退货 | 借：库存商品 / 贷：发出商品 |
| 发票红冲 | 借：发出商品 / 贷：销售成本 |

`periodic` 产品、手工出库（无销售订单行）和 dropship 不受影响；Odoo 原生 `stock.move.value`（FIFO/AVCO/标准价）计算不变。

已生成发出商品凭证的销售行会自动从以下位置排除，避免重复应计：

- 交货已入发出商品的行：从库存估值报表（Inventory Valuation）的
  Accruals / Invoices to be Issued 区、“待开具的发票 / Invoices To Be Issued”
  清单及应计订单向导的发票应计中排除；
- 退货已从发出商品转回库存的行：从库存估值报表的
  Accruals / Invoiced Not Delivered 区、“票已开货未发 / Invoiced Not Delivered”
  清单及应计订单向导的相应应计中排除。

仅排除实际存在对应发出商品/退货凭证的行；部分交货但未退货、periodic 产品、
dropship 和手工出库仍按原生逻辑参与应计。

公司间交易：

- 销售公司发往全局“Inter-company transit”库位的交货，视同客户交货，生成
  `借 发出商品 / 贷 库存商品`；
- 采购公司从该中转库位入库的收货不带销售订单行，不生成发出商品凭证；
- 公司间退货从该中转库位退回销售公司库存时，生成
  `借 库存商品 / 贷 发出商品`；
- 采购方（买方）退货的 move 同时带 `purchase_line_id` 和自动镜像的
  `sale_line_id`，不生成销售发出商品凭证；其镜像销售行从销售侧
  “待开具发票”应计中排除，由采购侧生成正确的
  `借 票到货未到 / 贷 库存商品`，不再额外生成销售 COGS 分录；
- 自动生成的跨公司红字发票（`in_refund` / `out_refund`）在启用 Storno
  的公司下，税额行强制采用红字规则：贷方余额显示为负数借方，借方余额显示为
  负数贷方，而不是正数反方向。

## 配置

1. 会计 → 配置 → 设置 → Inventory Valuation：设置公司级“发出商品科目”（Goods in Transit Account）。
2. 产品类别 → 会计页：可设置类别级“发出商品科目”，留空时使用公司默认。
3. 确保 real_time 产品类别已配置库存商品科目和 Stock Journal。

未配置发出商品科目时，real_time 销售交货和发票过账会给出明确的配置错误，不会静默降级。

## 依赖

`sale_stock`、`stock_account`、`account_accountant`。

## 安装与测试

```bash
make install MODULE=zd_goods_in_transit DB=Goody_test
make test MODULE=zd_goods_in_transit DB=Goody_test
```

## 已知限制

- 模块安装前已交货未开票的历史数据不会自动补建发出商品凭证，建议在期间边界上线或执行一次性补账脚本。
- 交货后若 landed cost/成本重估改变 `move.value`，已过账的交货凭证不会自动回溯更新；建议在交货前完成成本调整，或重置并重验交货。
- Kit/phantom BoM 需要组件与成品类别使用同一发出商品科目，否则中转科目无法对清。
- 每个发生公司间 real_time 销售的公司都必须配置自己的发出商品科目；公司间 transit 不在公司间自动清账。
- 公司间交易：销售公司发往全局 “Inter-company transit” 库位的交货会生成发出商品凭证；采购公司从该库位入库的收货不生成。上线前已完成的公司间交货不会自动补账。
