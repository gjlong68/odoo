# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    moves = env['stock.move'].search([
        ('purchase_line_id', '!=', False),
        ('sale_line_id', '!=', False),
        ('is_out', '=', True),
    ]).filtered(lambda move: move._is_intercompany_purchase_return_move())
    if not moves:
        return

    sale_lines = moves.sale_line_id
    pickings = moves.picking_id

    # Zero-qty lines created only by the return move can be removed.  A
    # confirmed order blocks product-line deletion, but the exact verified
    # line ids are allowed through the context flag.
    spurious_lines = sale_lines.filtered(
        lambda line: not line.product_uom_qty
        and not line.qty_invoiced
        and not line.invoice_lines
        and line.move_ids
        and all(
            move._is_intercompany_purchase_return_move()
            for move in line.move_ids
        )
    )
    if spurious_lines:
        spurious_lines.with_context(
            zd_allow_spurious_return_line_unlink=spurious_lines.ids,
        ).sudo().unlink()

    # Detach any remaining return moves from their sale lines.
    moves.sudo().write({'sale_line_id': False})

    # For pickings made only of intercompany purchase returns, clear the sales
    # order link too.  Mixed pickings keep their normal sale link.
    return_pickings = pickings.filtered(
        lambda picking: picking.move_ids
        and all(
            move._is_intercompany_purchase_return_move()
            for move in picking.move_ids
        )
    )
    return_pickings.sudo().write({'sale_id': False})
