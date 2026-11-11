# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.base.models.res_company import company_default_for


class ResCompany(models.Model):
    _inherit = "res.company"

    account_stock_transit_id = fields.Many2one(
        "account.account",
        string="Goods in Transit Account",
        **company_default_for(
            "account_stock_transit_id",
            "product.category",
            "property_stock_account_transit_id",
        ),
        check_company=True,
    )

    def _get_accrual_candidate_lines(self, date=False):
        candidates = super()._get_accrual_candidate_lines(date=date)
        lines = candidates.get("invoice_to_be_issued")
        if lines:
            # Goods already booked to Goods in Transit by the delivery entry
            # must not trigger an additional inventory/COGS accrual.
            candidates["invoice_to_be_issued"] = lines.filtered(
                lambda line: not line._has_goods_in_transit_entry()
                and not line._has_intercompany_purchase_return()
            )
        lines = candidates.get("invoiced_not_delivered")
        if lines:
            # Returns already reversed the transit entry; an 'invoiced not
            # delivered' accrual would duplicate it.
            candidates["invoiced_not_delivered"] = lines.filtered(
                lambda line: not line._has_goods_in_transit_return()
            )
        return candidates
