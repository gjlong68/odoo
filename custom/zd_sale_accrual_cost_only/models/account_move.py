# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        presentation.

        The mirrored refund created by the inter-company rules can keep its tax
        line as a positive opposite-side amount (e.g. credit 975 instead of
        debit -975) while the other lines are already storno.  Rewrite those
        tax lines to negative debit / negative credit on the original side.
        """
        for move in self:
            tax_lines = move.line_ids.filtered(
                lambda line: line.display_type in ('tax', 'non_deductible_tax')
                and not line.is_storno
            )
            for line in tax_lines:
                balance = line.balance
                if move.company_currency_id.is_zero(balance):
                    continue
                line.sudo().with_context(check_move_validity=False).write({
                    'is_storno': True,
                    'debit': balance if balance < 0 else 0.0,
                    'credit': -balance if balance > 0 else 0.0,
                })
