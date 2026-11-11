# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = "account.accrued.orders.wizard"

    def _filter_goods_in_transit(self, order_lines):
        if order_lines._name != "sale.order.line":
            return order_lines
        if self.accrual_type == "invoice_to_be_issued":
            return order_lines.filtered(
                lambda line: not line._has_goods_in_transit_entry()
                and not line._has_intercompany_purchase_return()
            )
        if self.accrual_type == "invoiced_not_delivered":
            return order_lines.filtered(
                lambda line: not line._has_goods_in_transit_return()
            )
        return order_lines

    def _get_accrual_main_line_vals(self, order_lines, accrual_entry_date):
        return super()._get_accrual_main_line_vals(
            self._filter_goods_in_transit(order_lines), accrual_entry_date
        )

    def _get_accrual_pending_cogs_vals(self, order_lines, accrual_entry_date):
        return super()._get_accrual_pending_cogs_vals(
            self._filter_goods_in_transit(order_lines), accrual_entry_date
        )
