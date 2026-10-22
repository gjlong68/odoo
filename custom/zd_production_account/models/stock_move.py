# -*- coding: utf-8 -*-

from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        self.ensure_one()
        vals = super()._prepare_analytic_line_values(account_field_values, amount, unit_amount)
        vals['zd_production_id'] = self.raw_material_production_id.id
        return vals
