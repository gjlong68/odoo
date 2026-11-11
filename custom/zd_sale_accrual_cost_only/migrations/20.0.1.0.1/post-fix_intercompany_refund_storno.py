# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    moves = env['account.move'].search([
        ('auto_generated', '=', True),
        ('move_type', 'in', ('in_refund', 'out_refund')),
        ('state', '=', 'posted'),
        ('company_id.account_storno', '=', True),
    ])
    moves._fix_intercompany_refund_storno()
