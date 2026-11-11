# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    def _get_accrual_main_line_vals(self, order_lines, accrual_entry_date):
        """Sales accruals must not recognize revenue.

        Core creates a revenue line (credit income) and its accrual counterpart
        (debit invoices_to_issue).  For sale order lines we drop both: the only
        entry left is the cost reclassification produced by
        ``_get_accrual_pending_cogs_vals``.
        """
        if order_lines._name == 'sale.order.line':
            return [], []
        return super()._get_accrual_main_line_vals(order_lines, accrual_entry_date)

    def _get_accrual_pending_cogs_vals(self, order_lines, accrual_entry_date):
        """Post the cost side of a sales accrual against the accrual account.

        Core posts ``Dr expense / Cr stock valuation``.  Replace the expense
        debit with ``invoices_to_issue`` (delivered, not invoiced) or
        ``invoiced_not_delivered`` (invoiced, not delivered) so the accrual
        only reclassifies the delivered goods' cost between balance-sheet
        accounts.
        """
        if order_lines._name != 'sale.order.line':
            return super()._get_accrual_pending_cogs_vals(order_lines, accrual_entry_date)

        filtered_lines = order_lines.filtered(
            lambda line: not line._is_intercompany_purchase_return_line()
        )
        if order_lines and not filtered_lines:
            raise UserError(_(
                "The selected sale order line mirrors an intercompany purchase "
                "return. Its cost is accrued on the purchase side, so no sales "
                "accrual is needed."
            ))
        order_lines = filtered_lines

        vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            # Reuse the core cost computation (standard price, or the posted
            # COGS unit price for the invoiced-not-delivered direction).
            line_vals, line_counterpart_vals = super()._get_accrual_pending_cogs_vals(
                order_line, accrual_entry_date,
            )
            if not line_vals:
                continue

            qty_to_invoice, __, __, __ = self._get_accrual_qty_price_and_amount(order_line)
            order = order_line.order_id
            product = order_line.product_id.with_company(order.company_id)
            accounts = product.product_tmpl_id.get_product_accounts(
                fiscal_pos=order.fiscal_position_id,
            )
            accrual_account = self.account_id or accounts[
                'invoices_to_issue' if qty_to_invoice > 0 else 'invoiced_not_delivered'
            ]
            if not accrual_account:
                continue

            for vals in line_counterpart_vals:
                vals['account_id'] = accrual_account.id
            for vals in line_vals + line_counterpart_vals:
                # These are ordinary balance-sheet reclassification lines, not
                # invoice COGS.  Keeping ``cogs`` would make
                # ``account.move.button_draft()`` unlink them.
                vals['display_type'] = 'product'
            vals_list += line_vals
            counterpart_vals_list += line_counterpart_vals

        return vals_list, self._merge_aml_vals(counterpart_vals_list)

    def _compute_move_vals(self):
        active_model = self.env.context.get('active_model')
        if self.amount and active_model in ('sale.order', 'sale.order.line'):
            raise UserError(_(
                "Sales accruals cannot use a manual amount. Select the sale "
                "order lines and let the accrual be computed from the "
                "delivered and invoiced quantities."
            ))
        return super()._compute_move_vals()
