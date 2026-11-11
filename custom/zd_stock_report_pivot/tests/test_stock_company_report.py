# -*- coding: utf-8 -*-

from lxml import etree

from odoo import Command, fields
from odoo.tests import TransactionCase, tagged

REPORT_MODEL = 'zd_stock_report_pivot.stock_company_report'


@tagged('post_install', '-at_install')
class TestStockCompanyReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'ZD Company Report B'})
        cls.env.user.company_ids |= cls.company_b
        cls.warehouse_a = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company_a.id)], limit=1)
        cls.warehouse_b = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.company_b.id)], limit=1)
        cls.category = cls.env['product.category'].create({
            'name': 'ZD Company Report Category',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'ZD Company Report Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
        })
        cls.env = cls.env(context=dict(
            cls.env.context,
            allowed_company_ids=[cls.company_a.id, cls.company_b.id],
        ))
        # Company-dependent costs: Amount is qty * the cost of the row company.
        cls.product.with_company(cls.company_a).standard_price = 10.0
        cls.product.with_company(cls.company_b).standard_price = 20.0
        quant_model = cls.env['stock.quant']
        quant_model._update_available_quantity(cls.product, cls.warehouse_a.lot_stock_id, 5.0)
        quant_model._update_available_quantity(cls.product, cls.warehouse_b.lot_stock_id, 3.0)

    def _report(self, **context):
        return self.env[REPORT_MODEL].with_context(**context)

    def test_company_grouping(self):
        groups = self._report()._read_group(
            [('product_id', '=', self.product.id)],
            ['company_id'],
            ['qty_available:sum', 'free_qty:sum', 'amount:sum'],
        )
        by_company = {company.id: (qty, free, amount) for company, qty, free, amount in groups}
        self.assertAlmostEqual(by_company[self.company_a.id][0], 5.0)
        self.assertAlmostEqual(by_company[self.company_b.id][0], 3.0)
        self.assertAlmostEqual(by_company[self.company_a.id][1], 5.0)
        self.assertAlmostEqual(by_company[self.company_b.id][1], 3.0)
        self.assertAlmostEqual(by_company[self.company_a.id][2], 50.0)  # 5 * 10
        self.assertAlmostEqual(by_company[self.company_b.id][2], 60.0)  # 3 * 20

    def test_category_grouping(self):
        groups = self._report()._read_group(
            [('product_id', '=', self.product.id)],
            ['categ_id'],
            ['qty_available:sum', 'amount:sum'],
        )
        self.assertEqual(len(groups), 1)
        category, quantity, amount = groups[0]
        self.assertEqual(category, self.category)
        self.assertAlmostEqual(quantity, 8.0)
        self.assertAlmostEqual(amount, 110.0)  # 5 * 10 + 3 * 20

    def test_direct_read(self):
        records = self._report().search([('product_id', '=', self.product.id)])
        self.assertEqual(len(records), 2)
        self.assertAlmostEqual(sum(records.mapped('qty_available')), 8.0)
        self.assertAlmostEqual(sum(records.mapped('free_qty')), 8.0)
        self.assertAlmostEqual(sum(records.mapped('amount')), 110.0)

    def test_variant_level_grouping(self):
        flavor = self.env['product.attribute'].create({
            'name': 'ZD Flavor',
            'value_ids': [
                Command.create({'name': 'Cream'}),
                Command.create({'name': 'Hazelnut'}),
            ],
        })
        template = self.env['product.template'].create({
            'name': 'C12P',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': flavor.id,
                'value_ids': [Command.set(flavor.value_ids.ids)],
            })],
        })
        variants = template.product_variant_ids
        self.assertEqual(len(variants), 2)
        variants[0].with_company(self.company_a).standard_price = 10.0
        variants[1].with_company(self.company_a).standard_price = 20.0
        quant_model = self.env['stock.quant']
        quant_model._update_available_quantity(variants[0], self.warehouse_a.lot_stock_id, 1.0)
        quant_model._update_available_quantity(variants[1], self.warehouse_a.lot_stock_id, 2.0)

        groups = self._report()._read_group(
            [('product_id', 'in', variants.ids)],
            ['product_id'],
            ['qty_available:sum', 'amount:sum'],
        )
        quantities = {product.id: (quantity, amount) for product, quantity, amount in groups}
        self.assertEqual(set(quantities), set(variants.ids))
        self.assertAlmostEqual(quantities[variants[0].id][0], 1.0)
        self.assertAlmostEqual(quantities[variants[1].id][0], 2.0)
        self.assertAlmostEqual(quantities[variants[0].id][1], 10.0)
        self.assertAlmostEqual(quantities[variants[1].id][1], 40.0)
        self.assertEqual(len({variant.display_name for variant in variants}), 2)

    def test_inventory_at_date(self):
        product = self.env['product.product'].create({
            'name': 'ZD Company Report Historical Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.category.id,
        })
        product.with_company(self.company_a).standard_price = 10.0
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        move = self.env['stock.move'].create({
            'origin': 'ZD Company Report Historical Receipt',
            'product_id': product.id,
            'product_uom_qty': 5.0,
            'uom_id': product.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.warehouse_a.lot_stock_id.id,
        })
        move._action_confirm()
        move.quantity = 5.0
        move.picked = True
        move._action_done()

        def values_at(to_date):
            groups = self._report(to_date=to_date)._read_group(
                [('product_id', '=', product.id), ('company_id', '=', self.company_a.id)],
                ['company_id'],
                ['qty_available:sum', 'amount:sum'],
            )
            return (groups[0][1], groups[0][2]) if groups else (0.0, 0.0)

        historical_qty, historical_amount = values_at('2000-01-01')
        self.assertAlmostEqual(historical_qty, 0.0)
        self.assertAlmostEqual(historical_amount, 0.0)
        current_qty, current_amount = values_at(fields.Date.today())
        self.assertAlmostEqual(current_qty, 5.0)
        self.assertAlmostEqual(current_amount, 50.0)

    def test_views_and_action(self):
        pivot = self.env.ref('zd_stock_report_pivot.stock_company_report_pivot')
        self.assertEqual(pivot.type, 'pivot')
        self.assertEqual(pivot.model, REPORT_MODEL)
        arch = etree.fromstring(pivot.arch)
        row_fields = [
            (field.get('name'), field.get('type'))
            for field in arch.xpath('//field[@type="row"]')
        ]
        self.assertEqual(row_fields, [
            ('company_id', 'row'),
            ('categ_id', 'row'),
            ('product_id', 'row'),
        ])
        measure_fields = [
            (field.get('name'), field.get('type'))
            for field in arch.xpath('//field[@type="measure"]')
        ]
        self.assertIn(('amount', 'measure'), measure_fields)

        action = self.env.ref('zd_stock_report_pivot.action_stock_company_report')
        self.assertEqual(action.res_model, REPORT_MODEL)
        self.assertIn('pivot', action.view_mode.split(','))
        self.assertTrue(self.env.ref('zd_stock_report_pivot.menu_stock_company_report'))

        search = self.env.ref('zd_stock_report_pivot.stock_company_report_search')
        search_arch = etree.fromstring(search.arch)
        contexts = {
            node.get('name'): node.get('context')
            for node in search_arch.xpath('//filter')
        }
        self.assertIn("'group_by': 'company_id'", contexts['group_by_company'])
        self.assertIn("'group_by': 'categ_id'", contexts['group_by_categ_id'])
        self.assertIn("'group_by': 'product_id'", contexts['group_by_product'])

    def test_wizard_stock_by_company(self):
        wizard = self.env['zd_stock_report_pivot.inventory_at_date'].create({
            'date': '2020-01-31',
        })
        action = wizard.action_open_stock_by_company()
        self.assertEqual(action['res_model'], REPORT_MODEL)
        self.assertIn('2020-01-31', action['name'])
        self.assertEqual(action['context']['to_date'], '2020-01-31')
        self.assertIn('pivot', action['view_mode'].split(','))

    def test_company_restriction(self):
        report_user = self.env['res.users'].create({
            'name': 'ZD Company Report User A',
            'login': 'zd_company_report_user_a',
            'group_ids': [Command.link(self.env.ref('stock.group_stock_user').id)],
            'company_id': self.company_a.id,
            'company_ids': [Command.set([self.company_a.id])],
        })
        report = self.env[REPORT_MODEL].with_user(report_user).with_context(
            allowed_company_ids=[self.company_a.id])
        groups = report._read_group(
            [('product_id', '=', self.product.id)],
            ['company_id'],
            ['qty_available:sum'],
        )
        self.assertEqual({company.id for company, _qty in groups}, {self.company_a.id})
        self.assertAlmostEqual(groups[0][1], 5.0)
