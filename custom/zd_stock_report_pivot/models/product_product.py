# -*- coding: utf-8 -*-

from odoo import models

QUANTITY_FIELDS = frozenset({
    'qty_available',
    'free_qty',
    'incoming_qty',
    'outgoing_qty',
    'virtual_available',
})


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _read_group_select(self, table, aggregate_spec):
        """Make the non-stored stock quantities aggregatable for pivot views."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in QUANTITY_FIELDS and aggregator == 'sum':
            return super()._read_group_select(table, 'id:recordset')
        return super()._read_group_select(table, aggregate_spec)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        """Sum the computed quantities of the products collected in each group."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in QUANTITY_FIELDS and aggregator == 'sum':
            records = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            return (
                sum((product[field_name] for product in products), 0.0)
                for products in records
            )
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)
