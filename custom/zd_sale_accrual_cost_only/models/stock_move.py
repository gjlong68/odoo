# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import models


def _is_intercompany_transit_location(location):
    """Whether ``location`` is the global inter-company transit location."""
    intercompany = location.env.ref(
        'stock.stock_location_inter_company', raise_if_not_found=False,
    )
    if intercompany:
        return location == intercompany
    return location.usage == 'transit' and not location.company_id


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_intercompany_purchase_return_move(self):
        """Whether this move returns goods from a purchase to the counterparty.

        Such a move carries ``purchase_line_id`` and goes to the global
        inter-company transit location.  It is a purchase return, not a sale
        delivery, and must not be synchronized onto a sale order.
        """
        self.ensure_one()
        return bool(
            self.purchase_line_id
            and self.is_out
            and _is_intercompany_transit_location(self.location_dest_id)
        )

    def _action_synch_order(self):
        """Do not let a purchase return create/link a sale order line.

        ``sale_stock`` processes any outgoing move to a customer/transit
        location as a sale delivery.  An intercompany purchase return has the
        same shape and would create a spurious sale line (and ``sale_line_id``)
        on the sale order referenced by the return picking.
        """
        moves = self.filtered(
            lambda move: not move._is_intercompany_purchase_return_move()
        )
        if not moves:
            return True
        return super(StockMove, moves)._action_synch_order()
