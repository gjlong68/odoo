# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

TRANSIT_ACCOUNT_DOMAIN = (
    "[('account_type', 'not in', "
    "('asset_receivable', 'liability_payable', 'asset_cash', "
    "'liability_credit_card', 'off_balance'))]"
)


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_stock_account_transit_id = fields.Many2one(
        "account.account",
        string="Goods in Transit Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        tracking=True,
        domain=TRANSIT_ACCOUNT_DOMAIN,
        help="Account holding the cost of goods delivered to customers but not "
             "yet invoiced. Used for sale-order deliveries and for the COGS of "
             "real-time-valued products. Leave empty to use the company default.",
    )
    property_stock_account_transit_active = fields.Boolean(
        related="property_stock_account_transit_id.active",
        string="Goods in Transit Account Active",
    )
