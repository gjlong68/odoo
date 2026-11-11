# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Command


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_intercompany_purchase_return_line(self):
        """Whether this line mirrors an intercompany purchase return.

        In an intercompany return, the outgoing move to the global
        inter-company transit location carries both ``purchase_line_id`` and
        ``sale_line_id``.  The purchase side already accrues the cost
        (``bills to receive`` / ``billed not received``); the mirrored sale
        line must not generate an additional ``invoices to be issued``
        accrual, and the return picking must not appear on the sale order.
        """
        self.ensure_one()
        return any(
            move._is_intercompany_purchase_return_move()
            for move in self.move_ids
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Do not let stock validation create a sale line for a purchase return.

        ``stock.picking._action_done()`` in ``sale_stock`` creates a zero-qty
        sale line for outgoing moves to a customer/transit location.  Skip
        those vals when every linked move is an intercompany purchase return.
        """
        filtered_vals_list = []
        for vals in vals_list:
            raw_move_ids = vals.get('move_ids') or []
            if not isinstance(raw_move_ids, (list, tuple)):
                raw_move_ids = []
            move_ids = [
                command[1]
                for command in raw_move_ids
                if isinstance(command, (list, tuple))
                and len(command) == 3
                and command[0] == Command.LINK
            ]
            moves = self.env['stock.move'].browse(move_ids).exists() if move_ids else self.env['stock.move']
            if moves and all(
                move._is_intercompany_purchase_return_move() for move in moves
            ):
                continue
            filtered_vals_list.append(vals)
        if not filtered_vals_list:
            return self.browse()
        return super().create(filtered_vals_list)

    def _check_line_unlink(self):
        """Allow the cleanup migration to remove verified spurious return lines.

        Stock validation can create a zero-qty sale line on a confirmed sale
        order.  Odoo normally refuses to delete confirmed-order lines; the
        migration passes the exact line ids it has verified as spurious.
        """
        lines = super()._check_line_unlink()
        allowed_ids = self.env.context.get(
            'zd_allow_spurious_return_line_unlink',
        ) or []
        if self.env.su and allowed_ids:
            lines -= self.filtered(lambda line: line.id in allowed_ids)
        return lines

    @api.model
    def _get_accrual_line_ids(self, mode=False, date=False, extra_domain=None):
        lines = super()._get_accrual_line_ids(
            mode=mode, date=date, extra_domain=extra_domain,
        )
        return lines.filtered(
            lambda line: not line._is_intercompany_purchase_return_line()
        )
