# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class InventoryAtDate(models.TransientModel):
    _name = 'zd_stock_report_pivot.inventory_at_date'
    _description = 'Inventory at Date'

    date = fields.Date(
        string='Inventory Date',
        required=True,
        default=fields.Date.context_today,
    )

    def action_open_inventory_at_date(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'stock.action_product_stock_view')
        action['name'] = self.env._('Inventory at Date: %(date)s', date=self.date)
        context = safe_eval(action.get('context') or '{}')
        # A date-only string is converted by the core to the end of that day.
        context['to_date'] = self.date.strftime('%Y-%m-%d')
        action['context'] = context
        return action

    def action_open_stock_by_company(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'zd_stock_report_pivot.action_stock_company_report')
        action['name'] = self.env._('Stock by Company: %(date)s', date=self.date)
        context = safe_eval(action.get('context') or '{}')
        # The report forwards to_date to the core quantity computation.
        context['to_date'] = self.date.strftime('%Y-%m-%d')
        action['context'] = context
        return action
