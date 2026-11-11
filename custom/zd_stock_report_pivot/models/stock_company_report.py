# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models, tools
from odoo.tools import SQL

QUANTITY_FIELDS = (
    'qty_available',
    'free_qty',
    'incoming_qty',
    'outgoing_qty',
    'virtual_available',
)

# Computed values that are aggregated with the ``id:recordset`` trick below.
AGGREGATE_FIELDS = QUANTITY_FIELDS + ('amount',)


class StockCompanyReport(models.Model):
    _name = 'zd_stock_report_pivot.stock_company_report'
    _description = 'Stock by Company'
    _auto = False
    _order = 'company_id, categ_id, product_id'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', readonly=True)
    categ_id = fields.Many2one('product.category', 'Product Category', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    qty_available = fields.Float('On Hand', compute='_compute_quantities', compute_sudo=False)
    free_qty = fields.Float('Free to Use', compute='_compute_quantities', compute_sudo=False)
    incoming_qty = fields.Float('Incoming', compute='_compute_quantities', compute_sudo=False)
    outgoing_qty = fields.Float('Outgoing', compute='_compute_quantities', compute_sudo=False)
    virtual_available = fields.Float('Forecasted', compute='_compute_quantities', compute_sudo=False)
    amount = fields.Float(
        'Amount',
        compute='_compute_quantities',
        compute_sudo=False,
        help="Value of the quantity on hand, using the product cost in the row company.",
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW %s AS (
            WITH pairs AS (
                -- Current internal stock
                SELECT q.product_id,
                       COALESCE(l.company_id, lw.company_id) AS company_id
                FROM stock_quant q
                JOIN stock_location l ON l.id = q.location_id
                LEFT JOIN stock_warehouse lw ON lw.id = l.warehouse_id
                WHERE l.usage = 'internal'
                  AND (q.quantity != 0 OR q.reserved_quantity != 0)
                UNION
                -- Pending and done moves: done moves keep past product/company
                -- pairs available when the current quants are already unlinked.
                SELECT m.product_id,
                       CASE
                           WHEN sl.usage = 'internal'
                               THEN COALESCE(sl.company_id, slw.company_id, dl.company_id, dlw.company_id)
                           ELSE COALESCE(dl.company_id, dlw.company_id, sl.company_id, slw.company_id)
                       END AS company_id
                FROM stock_move m
                LEFT JOIN stock_location sl ON sl.id = m.location_id
                LEFT JOIN stock_warehouse slw ON slw.id = sl.warehouse_id
                LEFT JOIN stock_location dl
                       ON dl.id = CASE
                           WHEN m.state = 'done' THEN m.location_dest_id
                           ELSE COALESCE(m.forecasted_location_id, m.location_dest_id)
                       END
                LEFT JOIN stock_warehouse dlw ON dlw.id = dl.warehouse_id
                WHERE (
                        m.state = 'done'
                        OR m.state IN ('waiting', 'confirmed', 'assigned', 'partially_available')
                    )
                  AND (m.product_qty != 0 OR m.quantity != 0)
                  AND (sl.usage = 'internal' OR dl.usage = 'internal')
            )
            SELECT ROW_NUMBER() OVER (ORDER BY p.product_id, p.company_id) AS id,
                   p.product_id,
                   pp.product_tmpl_id,
                   pt.categ_id,
                   p.company_id
            FROM pairs p
            JOIN product_product pp ON pp.id = p.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE p.company_id IS NOT NULL
              AND pt.is_storable = true
            )
        """, SQL.identifier(self._table)))

    @api.depends('product_id', 'company_id')
    @api.depends_context('to_date', 'from_date', 'lot_id', 'owner_id', 'package_id')
    def _compute_quantities(self):
        values = self._get_quantities_dict()
        for record in self:
            data = values.get((record.product_id.id, record.company_id.id), {})
            for field_name in AGGREGATE_FIELDS:
                record[field_name] = data.get(field_name, 0.0)

    def _get_quantities_dict(self):
        """Return {(product_id, company_id): {quantity field: value}}.

        The report rows are (product, company) pairs, while the quantity
        fields are computed per product for the warehouses of a single
        company. Calling the core product computation with
        ``allowed_company_ids`` restricted to that company gives the exact
        same semantics as the standard Stock report, including ``to_date``.
        """
        result = {}
        by_company = defaultdict(lambda: self.env['product.product'])
        for record in self:
            if record.product_id and record.company_id:
                by_company[record.company_id] |= record.product_id
        ctx = self.env.context
        for company, products in by_company.items():
            products_company = products.with_context(allowed_company_ids=company.ids)
            quantities = products_company._compute_quantities_dict(
                ctx.get('lot_id'),
                ctx.get('owner_id'),
                ctx.get('package_id'),
                ctx.get('from_date'),
                ctx.get('to_date'),
            )
            # ``standard_price`` is company-dependent: env.company is the row
            # company here, so the cost matches the company of the row.
            standard_prices = {product.id: product.standard_price for product in products_company}
            for product in products:
                data = dict(quantities.get(product.id, {}))
                data['amount'] = data.get('qty_available', 0.0) * standard_prices.get(product.id, 0.0)
                result[(product.id, company.id)] = data
        return result

    def _read_group_select(self, table, aggregate_spec):
        """Make the computed quantities and amounts aggregatable for pivot/list views."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in AGGREGATE_FIELDS and aggregator == 'sum':
            return super()._read_group_select(table, 'id:recordset')
        return super()._read_group_select(table, aggregate_spec)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        """Sum the computed quantities and amounts of the (product, company) rows in each group."""
        field_name, _sep, aggregator = aggregate_spec.partition(':')
        if field_name in AGGREGATE_FIELDS and aggregator == 'sum':
            groups = list(super()._read_group_postprocess_aggregate('id:recordset', raw_values))
            all_records = self.browse({record.id for group in groups for record in group})
            values = all_records._get_quantities_dict()
            return (
                sum(
                    values.get((record.product_id.id, record.company_id.id), {}).get(field_name, 0.0)
                    for record in group
                )
                for group in groups
            )
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)
