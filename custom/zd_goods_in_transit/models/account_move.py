# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted.filtered(
            lambda move: move.auto_generated
            and move.is_refund()
            and move.company_id.account_storno
        )._fix_intercompany_refund_storno()
        return posted

    def _fix_intercompany_refund_storno(self):
        """Force tax lines of auto-generated inter-company refunds into storno
        presentation: negative debit / negative credit on the original side,
        instead of a positive opposite-side amount."""
        for move in self:
            tax_lines = move.line_ids.filtered(
                lambda line: line.display_type in ("tax", "non_deductible_tax")
                and not line.is_storno
            )
            for line in tax_lines:
                balance = line.balance
                if move.company_currency_id.is_zero(balance):
                    continue
                line.sudo().with_context(check_move_validity=False).write({
                    "is_storno": True,
                    "debit": balance if balance < 0 else 0.0,
                    "credit": -balance if balance > 0 else 0.0,
                })

    def _get_cogs_lines_vals(self):
        vals_list = super()._get_cogs_lines_vals()
        if not vals_list:
            return vals_list

        invoice_lines = {line.id: line for line in self.invoice_line_ids}
        cache = {}
        for vals in vals_list:
            line = invoice_lines.get(vals.get("cogs_origin_id"))
            if not line or not line._use_inventory_valuation():
                continue
            if line.id not in cache:
                template = line.product_id.with_company(self.company_id).product_tmpl_id
                cache[line.id] = (
                    template.get_product_accounts(fiscal_pos=self.fiscal_position_id),
                    template._get_checked_stock_transit_account(),
                )
            mapped_accounts, transit = cache[line.id]
            if vals["account_id"] == mapped_accounts["stock_valuation"].id:
                vals["account_id"] = transit.id
        return vals_list
