# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _has_goods_in_transit_entry(self):
        """Whether this sale line has a delivery whose cost already sits in
        the Goods in Transit account."""
        self.ensure_one()
        return any(
            move.account_move_id and move._is_goods_in_transit_move()
            for move in self.move_ids
        )

    def _has_goods_in_transit_return(self):
        """Whether this sale line has a customer return whose cost has already
        been moved back from Goods in Transit to stock."""
        self.ensure_one()
        return any(
            move.account_move_id
            and move.is_in
            and (
                move.location_id.usage == "customer"
                or move._is_intercompany_transit_location(move.location_id)
            )
            and move._is_goods_in_transit_move()
            for move in self.move_ids
        )

    def _has_intercompany_purchase_return(self):
        """Whether this sale line is the auto-generated mirror of a purchase
        return: the physical move is linked to a purchase line and leaves the
        buyer's stock for the inter-company transit location. Such a line must
        not generate a sales 'invoices to be issued' accrual; the purchase side
        books Dr Billed Not Received / Cr Stock Valuation instead."""
        self.ensure_one()
        return any(
            move.purchase_line_id
            and move.is_out
            and move._is_intercompany_transit_location(move.location_dest_id)
            for move in self.move_ids
        )

    @api.model
    def _get_accrual_line_ids(self, mode=False, date=False, extra_domain=None):
        lines = super()._get_accrual_line_ids(
            mode=mode, date=date, extra_domain=extra_domain
        )
        if mode == "invoice_issued":
            # The delivery entry already booked the cost to Goods in Transit;
            # an 'invoices to be issued' accrual would duplicate it. The
            # auto-generated mirror of a purchase return is accrued on the
            # purchase side instead.
            lines = lines.filtered(
                lambda line: not line._has_goods_in_transit_entry()
                and not line._has_intercompany_purchase_return()
            )
        elif mode == "deferred":
            # The return entry already moved the cost back to stock;
            # an 'invoiced not delivered' accrual would duplicate it.
            lines = lines.filtered(
                lambda line: not line._has_goods_in_transit_return()
            )
        return lines
