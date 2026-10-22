# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestZdProductionAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.production_account = cls.env['account.account'].create({
            'name': 'ZD Production Cost',
            'code': 'ZD990001',
            'account_type': 'expense_direct_cost',
        })
        cls.category = cls.env['product.category'].create({
            'name': 'ZD Test Category',
            'property_stock_account_production_cost_id': cls.production_account.id,
        })
        cls.finished = cls.env['product.product'].create({
            'name': 'ZD Finished Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
        })
        cls.component = cls.env['product.product'].create({
            'name': 'ZD Component',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
        })
        cls.production = cls.env['mrp.production'].create({
            'product_id': cls.finished.id,
            'product_qty': 1.0,
            'uom_id': cls.finished.uom_id.id,
        })
        cls.raw_move = cls.env['stock.move'].create({
            'product_id': cls.component.id,
            'product_uom_qty': 1.0,
            'uom_id': cls.component.uom_id.id,
            'location_id': cls.production.location_src_id.id,
            'location_dest_id': cls.production.production_location_id.id,
            'raw_material_production_id': cls.production.id,
        })
        cls.plan = cls.env.ref('analytic.analytic_plan_projects')
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'ZD Analytic Account',
            'plan_id': cls.plan.id,
        })

    def test_prepare_analytic_line_values(self):
        column = self.plan._column_name()
        vals = self.raw_move._prepare_analytic_line_values(
            {column: self.analytic_account.id}, 10.0, 1.0,
        )
        self.assertEqual(vals['zd_production_id'], self.production.id)
        self.assertEqual(vals['general_account_id'], self.production_account.id)
        self.assertEqual(vals[column], self.analytic_account.id)
        self.assertAlmostEqual(vals['amount'], 10.0)
        self.assertAlmostEqual(vals['unit_amount'], 1.0)

        line = self.env['account.analytic.line'].create(vals)
        self.assertEqual(line.zd_production_id, self.production)
        self.assertEqual(line.general_account_id, self.production_account)
        self.assertEqual(line[column], self.analytic_account)
