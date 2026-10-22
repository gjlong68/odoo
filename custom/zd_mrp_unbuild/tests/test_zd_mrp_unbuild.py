# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestZdMrpUnbuild(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.product = cls.env['product.product'].create({
            'name': 'ZD Unbuild Product',
            'type': 'consu',
            'is_storable': True,
        })
        cls.plan = cls.env.ref('analytic.analytic_plan_projects')
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'ZD Unbuild Analytic',
            'plan_id': cls.plan.id,
        })
        cls.project = cls.env['project.project'].create({
            'name': 'ZD Unbuild Project',
            'account_id': cls.analytic_account.id,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'project_id': cls.project.id,
        })
        cls.unbuild = cls.env['mrp.unbuild'].create({
            'product_id': cls.product.id,
            'product_qty': 1.0,
            'uom_id': cls.product.uom_id.id,
            'bom_id': cls.bom.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.stock_location.id,
        })

    def _new_move(self, **extra):
        return self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': 1.0,
            'uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            **extra,
        })

    def test_analytic_project_from_bom(self):
        self.assertEqual(self.unbuild._get_analytic_project(), self.project)

    def test_analytic_project_prefers_manufacturing_order(self):
        mo_project = self.env['project.project'].create({
            'name': 'ZD MO Project',
            'account_id': self.analytic_account.id,
        })
        production = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 1.0,
            'uom_id': self.product.uom_id.id,
            'bom_id': self.bom.id,
            'project_id': mo_project.id,
        })
        unbuild = self.env['mrp.unbuild'].create({
            'product_id': self.product.id,
            'product_qty': 1.0,
            'uom_id': self.product.uom_id.id,
            'mo_id': production.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        self.assertEqual(unbuild._get_analytic_project(), mo_project)
        self.assertEqual(
            unbuild._get_analytic_project()._get_analytic_distribution(),
            {str(self.analytic_account.id): 100},
        )

    def test_analytic_distribution_on_unbuild_moves(self):
        expected = {str(self.analytic_account.id): 100}
        produce_move = self._new_move(unbuild_id=self.unbuild.id)
        consume_move = self._new_move(consume_unbuild_id=self.unbuild.id)
        self.assertEqual(produce_move._get_analytic_distribution(), expected)
        self.assertEqual(consume_move._get_analytic_distribution(), expected)

    def test_create_analytic_move_for_unbuild(self):
        """Unbuild moves have no picking type, so the core override skips them."""
        moves = self._new_move(unbuild_id=self.unbuild.id) | self._new_move(consume_unbuild_id=self.unbuild.id)
        moves.write({'state': 'done', 'value': 100.0})
        moves._create_analytic_move()
        for move in moves:
            self.assertEqual(len(move.analytic_account_line_ids), 1)
            self.assertEqual(move.analytic_account_line_ids.account_id, self.analytic_account)
            self.assertEqual(move.analytic_account_line_ids.amount, 100.0)
