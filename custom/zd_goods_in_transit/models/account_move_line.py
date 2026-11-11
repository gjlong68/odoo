# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _set_cogs(self):
        """Re-evaluate COGS lines.

        The stock side may now sit on the Goods in Transit account instead of
        the Stock Valuation account, so both must be recognized as the stock
        side when revaluing a posted COGS entry.
        """
        self = self.sudo()  # noqa: PLW0642
        for invoice_line in self.cogs_origin_id:
            account_move = invoice_line.move_id
            if account_move.state != "posted":
                continue
            invoice_line = invoice_line.with_company(account_move.company_id)
            template = invoice_line.product_id.product_tmpl_id
            mapped = template.get_product_accounts(
                fiscal_pos=account_move.fiscal_position_id
            )
            raw = template._get_product_accounts()
            stock_side_accounts = (
                mapped["stock_valuation"]
                | raw["stock_valuation"]
                | mapped["stock_transit"]
                | raw["stock_transit"]
            )

            sign = -1 if account_move.move_type == "out_refund" else 1
            qty = invoice_line.product_uom_id._compute_quantity(
                invoice_line.quantity, invoice_line.product_id.uom_id
            )
            price_unit = invoice_line.cogs_move_ids._get_price_unit(
                include_consigned=True, product=invoice_line.product_id
            )
            amount = sign * qty * price_unit

            cogs_lines = self.filtered(
                lambda line, inv_line=invoice_line: line.display_type == "cogs"
                and line.cogs_origin_id == inv_line
            )
            for line in cogs_lines:
                on_stock_account = line.account_id in stock_side_accounts
                line.with_context(check_move_validity=False).write({
                    "price_unit": price_unit if on_stock_account else -price_unit,
                    "amount_currency": -amount if on_stock_account else amount,
                    "balance": -amount if on_stock_account else amount,
                })
