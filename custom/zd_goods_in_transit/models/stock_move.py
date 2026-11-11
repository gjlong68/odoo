# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_intercompany_transit_location(self, location):
        """Whether `location` is the global inter-company transit location."""
        self.ensure_one()
        intercompany = self.env.ref(
            "stock.stock_location_inter_company", raise_if_not_found=False
        )
        if intercompany:
            return location == intercompany
        return location.usage == "transit" and not location.company_id

    def _is_goods_in_transit_move(self):
        """Whether this move must carry a Goods in Transit entry."""
        self.ensure_one()
        product = self.product_id.with_company(self.company_id)
        return bool(
            self.sale_line_id
            and not self.is_dropship
            and not self._should_exclude_for_valuation()
            and product.is_storable
            and product.valuation == "real_time"
            and not self.uom_id.is_zero(self.quantity)
            and not self.company_id.currency_id.is_zero(self.value)
            and (
                (
                    self.is_out
                    and (
                        self.location_dest_id.usage == "customer"
                        or (
                            not self.purchase_line_id
                            and self._is_intercompany_transit_location(
                                self.location_dest_id
                            )
                        )
                    )
                )
                or (
                    self.is_in
                    and (
                        self.location_id.usage == "customer"
                        or (
                            not self.purchase_line_id
                            and self._is_intercompany_transit_location(
                                self.location_id
                            )
                        )
                    )
                )
            )
        )

    def _should_create_account_move(self):
        if super()._should_create_account_move():
            return True
        return self._is_goods_in_transit_move()

    def _get_account_move_line_vals(self):
        if not self._is_goods_in_transit_move():
            return super()._get_account_move_line_vals()

        template = self.product_id.with_company(self.company_id).product_tmpl_id
        transit = template._get_checked_stock_transit_account()
        stock_account = template._get_product_accounts()["stock_valuation"]
        if not self.company_id.account_stock_journal_id:
            raise UserError(_(
                "No Stock Journal is configured for company %s. Configure it "
                "in Accounting settings > Inventory Valuation.",
                self.company_id.display_name,
            ))

        # If a location valuation account already produced a native entry, keep
        # its clearing lines and append the transit pair so both stay balanced.
        aml_vals = (
            super()._get_account_move_line_vals()
            if super()._should_create_account_move()
            else []
        )
        amount = self.value if self.is_in else -self.value
        common = {
            "name": f"{self.reference} - {self.product_id.name}",
            "product_id": self.product_id.id,
        }
        if self.is_in:
            # Customer return: reverse the delivery entry.
            aml_vals += [
                {**common, "account_id": stock_account.id, "debit": amount, "credit": 0.0},
                {**common, "account_id": transit.id, "debit": 0.0, "credit": amount},
            ]
        else:
            # Sale-order delivery.
            aml_vals += [
                {**common, "account_id": stock_account.id, "debit": 0.0, "credit": amount},
                {**common, "account_id": transit.id, "debit": amount, "credit": 0.0},
            ]
        return aml_vals
