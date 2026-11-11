# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        accounts["stock_transit"] = self._get_stock_transit_account()
        return accounts

    def _get_stock_transit_account(self):
        """Return the Goods in Transit account: category hierarchy first, then
        the company-level default."""
        self.ensure_one()
        return self._get_category_account(
            "property_stock_account_transit_id",
            "account_stock_transit_id",
        )

    def _get_checked_stock_transit_account(self):
        """Return the transit account or raise a configuration error."""
        self.ensure_one()
        accounts = self._get_product_accounts()
        transit = accounts["stock_transit"]
        if not accounts["stock_valuation"]:
            raise UserError(_(
                "No Stock Valuation account is configured for product %s.",
                self.display_name,
            ))
        if not transit:
            raise UserError(_(
                "No Goods in Transit account is configured for product %s "
                "(category: %s). Set it on the product category or in "
                "Accounting settings > Inventory Valuation.",
                self.display_name,
                self.categ_id.display_name or _("None"),
            ))
        if transit == accounts["stock_valuation"]:
            raise UserError(_(
                "The Goods in Transit account must differ from the Stock "
                "Valuation account for product %s.",
                self.display_name,
            ))
        return transit
