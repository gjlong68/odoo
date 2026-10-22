# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_analytic_distribution(self):
        """Use the unbuild order's project distribution for its stock moves.

        Odoo 20 computes analytic costs from ``_get_analytic_distribution()``.
        ``project_mrp_account`` covers manufacturing moves through
        ``raw_material_production_id.project_id``; this covers the unbuild side
        (``unbuild_id`` and ``consume_unbuild_id``), which is the reverse flow.
        """
        unbuild = self.unbuild_id or self.consume_unbuild_id
        if unbuild:
            distribution = unbuild._get_analytic_project()._get_analytic_distribution()
            if distribution:
                return distribution
        return super()._get_analytic_distribution()

    def _create_analytic_move(self):
        """Generate analytic lines for unbuild moves.

        ``project_stock_account`` only processes moves whose picking type has
        ``analytic_costs`` enabled. ``mrp.unbuild`` has no picking type in
        Odoo 20, so its moves would be skipped. Handle them here first, then
        let the regular flow process the remaining moves.
        """
        unbuild_moves = self.filtered(lambda move: move.unbuild_id or move.consume_unbuild_id)
        for move in unbuild_moves:
            analytic_line_vals = move._prepare_analytic_lines()
            if analytic_line_vals:
                move.analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(analytic_line_vals)
        return super()._create_analytic_move()
