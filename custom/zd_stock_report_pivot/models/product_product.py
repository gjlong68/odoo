# -*- coding: utf-8 -*-

from odoo import api, fields, models

QUANTITY_FIELDS = frozenset({
    'qty_available',
    'free_qty',
    'incoming_qty',
    'outgoing_qty',
    'virtual_available',
})

# Computed values that are aggregated with the ``id:recordset`` trick below.
AGGREGATE_FIELDS = QUANTITY_FIELDS | {'amount'}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    amount = fields.Float(
        'Amount',
        compute='_compute_amount',
        compute_sudo=False,
        help="Value of the quantity on hand, using the product cost.",
    )

    @api.depends('qty_available', 'standard_price')
    def _compute_amount(self):
        for product in self:
            product.amount = product.qty_available * product.standard_price

    def _read_group_select(self, table, aggregate_spec):
        """Make the non-stored stock quantities and amounts aggregatable for pivot views."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in AGGREGATE_FIELDS and aggregator == 'sum':
            return super()._read_group_select(table, 'id:recordset')
        return super()._read_group_select(table, aggregate_spec)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        """Sum the computed quantities and amounts of the products collected in each group."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in AGGREGATE_FIELDS and aggregator == 'sum':
            records = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            return (
                sum((product[field_name] for product in products), 0.0)
                for products in records
            )
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)
