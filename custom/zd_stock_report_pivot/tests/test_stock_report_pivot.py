# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestStockReportPivot(TransactionCase):

    QUANTITY_FIELDS = (
        'qty_available',
        'free_qty',
        'incoming_qty',
        'outgoing_qty',
        'virtual_available',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['product.category'].create({
            'name': 'ZD Pivot Test Category',
        })
        cls.product_1 = cls.env['product.product'].create({
            'name': 'ZD Pivot Product 1',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'ZD Pivot Product 2',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
        })
        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        cls.location = warehouse.lot_stock_id or cls.env.ref('stock.stock_location_stock')
        quant_model = cls.env['stock.quant']
        quant_model._update_available_quantity(cls.product_1, cls.location, 5.0)
        quant_model._update_available_quantity(cls.product_2, cls.location, 7.0)
        (cls.product_1 | cls.product_2).invalidate_recordset(list(cls.QUANTITY_FIELDS))

    def test_pivot_view_and_action(self):
        view = self.env.ref('zd_stock_report_pivot.product_product_stock_pivot')
        self.assertEqual(view.type, 'pivot')
        self.assertEqual(view.model, 'product.product')
        self.assertEqual(view.mode, 'primary')
        self.assertEqual(
            self.env['ir.ui.view'].default_view('product.product', 'pivot'),
            view.id,
        )
        action = self.env.ref('stock.action_product_stock_view')
        self.assertIn('pivot', action.view_mode.split(','))
        self.assertTrue(any(pair[1] == 'pivot' for pair in action.views))

    def test_read_group_non_stored_quantity(self):
        groups = self.env['product.product']._read_group(
            [('id', 'in', (self.product_1 | self.product_2).ids)],
            ['categ_id'],
            ['qty_available:sum'],
        )
        self.assertEqual(len(groups), 1)
        category, quantity = groups[0]
        self.assertEqual(category, self.category)
        self.assertAlmostEqual(quantity, 12.0)

    def test_formatted_grouping_sets(self):
        aggregates = [f'{field}:sum' for field in self.QUANTITY_FIELDS]
        by_category, by_product = self.env['product.product'].formatted_read_grouping_sets(
            [('id', 'in', (self.product_1 | self.product_2).ids)],
            [['categ_id'], ['categ_id', 'product_tmpl_id']],
            aggregates,
        )

        category_rows = {
            item['categ_id'][0]: item
            for item in by_category
            if item['categ_id']
        }
        row = category_rows[self.category.id]
        self.assertAlmostEqual(row['qty_available:sum'], 12.0)
        self.assertAlmostEqual(row['free_qty:sum'], 12.0)
        self.assertAlmostEqual(row['incoming_qty:sum'], 0.0)
        self.assertAlmostEqual(row['outgoing_qty:sum'], 0.0)
        self.assertAlmostEqual(row['virtual_available:sum'], 12.0)

        quantities = {
            item['product_tmpl_id'][0]: item['qty_available:sum']
            for item in by_product
            if item['product_tmpl_id']
        }
        self.assertAlmostEqual(quantities[self.product_1.product_tmpl_id.id], 5.0)
        self.assertAlmostEqual(quantities[self.product_2.product_tmpl_id.id], 7.0)

    def test_inventory_at_date_wizard_action(self):
        wizard = self.env['zd_stock_report_pivot.inventory_at_date'].create({
            'date': '2020-01-31',
        })
        action = wizard.action_open_inventory_at_date()
        self.assertEqual(action['res_model'], 'product.product')
        self.assertIn('2020-01-31', action['name'])
        self.assertEqual(action['context']['to_date'], '2020-01-31')
        self.assertIn('pivot', action['view_mode'].split(','))
        self.assertTrue(any(view[1] == 'pivot' for view in action['views']))

    def test_inventory_at_date_historical_quantities(self):
        product = self.env['product.product'].create({
            'name': 'ZD Historical Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.category.id,
        })
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        move = self.env['stock.move'].create({
            'origin': 'ZD Historical Receipt',
            'product_id': product.id,
            'product_uom_qty': 5.0,
            'uom_id': product.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.location.id,
        })
        move._action_confirm()
        move.quantity = 5.0
        move.picked = True
        move._action_done()

        def qty_at(to_date):
            groups = self.env['product.product'].with_context(to_date=to_date)._read_group(
                [('id', '=', product.id)], ['categ_id'], ['qty_available:sum'])
            return groups[0][1]

        self.assertAlmostEqual(qty_at('2000-01-01'), 0.0)
        self.assertAlmostEqual(qty_at(fields.Date.today()), 5.0)
