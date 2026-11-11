# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_transit_account_id = fields.Many2one(
        "account.account",
        string="Goods in Transit Account",
        readonly=False,
        related="company_id.account_stock_transit_id",
        check_company=True,
    )
    stock_transit_account_active = fields.Boolean(
        related="stock_transit_account_id.active",
        string="Goods in Transit Account Active",
    )
