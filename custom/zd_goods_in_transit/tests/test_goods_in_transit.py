# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestGoodsInTransit(TestStockValuationCommon, TestSaleStockCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.account_stock_transit = cls.env["account.account"].with_company(cls.company).create({
            "name": "Goods in Transit",
            "code": "110599",
            "account_type": "asset_current",
        })
        cls.company.account_stock_transit_id = cls.account_stock_transit
        cls.category_standard_auto.with_company(cls.company).property_stock_account_transit_id = (
            cls.account_stock_transit
        )

        cls.customer = cls.env["res.partner"].create({"name": "GIT Customer"})
        cls.product_delivery = cls.env["product.product"].create({
            "name": "GIT delivery product",
            "standard_price": 42.0,
            "is_storable": True,
            "categ_id": cls.category_standard_auto.id,
            "uom_id": cls.uom.id,
            "invoice_policy": "delivery",
        })
        cls.product_order = cls.env["product.product"].create({
            "name": "GIT order product",
            "standard_price": 13.0,
            "is_storable": True,
            "categ_id": cls.category_standard_auto.id,
            "uom_id": cls.uom.id,
            "invoice_policy": "order",
        })

    def _posted_balance(self, account):
        lines = self.env["account.move.line"].search([
            ("account_id", "=", account.id),
            ("move_id.state", "=", "posted"),
            ("company_id", "=", self.company.id),
        ])
        return sum(lines.mapped("balance"))

    def _stock_and_deliver(self, product, quantity=1, price=66.0):
        self._make_in_move(product, quantity, product.standard_price)
        return self._so_deliver(
            product, quantity=quantity, price=price, partner=self.customer
        )

    # ------------------------------------------------------------------
    # Delivery / invoice / refund / return
    # ------------------------------------------------------------------

    def test_delivery_creates_transit_entry(self):
        so = self._stock_and_deliver(self.product_delivery)
        move = so.picking_ids.move_ids
        self.assertEqual(len(move), 1)
        entry = move.account_move_id
        self.assertTrue(entry)
        self.assertEqual(entry.state, "posted")
        self.assertEqual(entry.journal_id, self.company.account_stock_journal_id)
        self.assertRecordValues(entry.line_ids.sorted("balance"), [
            {
                "account_id": self.account_stock_valuation.id,
                "balance": -42.0,
                "debit": 0.0,
                "credit": 42.0,
            },
            {
                "account_id": self.account_stock_transit.id,
                "balance": 42.0,
                "debit": 42.0,
                "credit": 0.0,
            },
        ])
        self.assertAlmostEqual(move.value, -42.0)

    def test_invoice_uses_transit_for_cogs(self):
        so = self._stock_and_deliver(self.product_delivery)
        invoice = so._create_invoices()
        invoice.action_post()

        cogs = invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertEqual(len(cogs), 2)
        self.assertRecordValues(cogs.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -42.0},
            {"account_id": self.account_expense.id, "balance": 42.0},
        ])
        self.assertFalse(
            invoice.line_ids.filtered(
                lambda line: line.account_id == self.account_stock_valuation
            )
        )
        self.assertAlmostEqual(self._posted_balance(self.account_stock_transit), 0.0)
        self.assertAlmostEqual(self._posted_balance(self.account_stock_valuation), -42.0)

    def test_refund_reverses_cogs(self):
        so = self._stock_and_deliver(self.product_delivery)
        invoice = so._create_invoices()
        invoice.action_post()
        refund = self._refund(invoice)

        cogs = refund.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertEqual(len(cogs), 2)
        self.assertRecordValues(cogs.sorted("balance"), [
            {"account_id": self.account_expense.id, "balance": -42.0},
            {"account_id": self.account_stock_transit.id, "balance": 42.0},
        ])
        self.assertAlmostEqual(self._posted_balance(self.account_expense), 0.0)

    def test_return_reverses_delivery(self):
        so = self._stock_and_deliver(self.product_delivery)
        delivery_move = so.picking_ids.move_ids
        return_moves = self._make_return(delivery_move, 1)
        self.assertEqual(len(return_moves), 1)
        return_move = return_moves
        self.assertTrue(return_move.sale_line_id)

        entry = return_move.account_move_id
        self.assertTrue(entry)
        self.assertEqual(entry.state, "posted")
        self.assertRecordValues(entry.line_ids.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -42.0},
            {"account_id": self.account_stock_valuation.id, "balance": 42.0},
        ])
        self.assertAlmostEqual(self._posted_balance(self.account_stock_transit), 0.0)
        self.assertAlmostEqual(self._posted_balance(self.account_stock_valuation), 0.0)

    def test_invoice_before_delivery(self):
        self._make_in_move(self.product_order, 1, self.product_order.standard_price)
        so = self._so_deliver(
            self.product_order, quantity=1, price=66.0,
            partner=self.customer, picking=False,
        )
        invoice = so._create_invoices()
        invoice.action_post()

        cogs = invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertRecordValues(cogs.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -13.0},
            {"account_id": self.account_expense.id, "balance": 13.0},
        ])

        picking = so.picking_ids
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking.button_validate()
        delivery_move = picking.move_ids
        entry = delivery_move.account_move_id
        self.assertTrue(entry)
        self.assertRecordValues(entry.line_ids.sorted("balance"), [
            {"account_id": self.account_stock_valuation.id, "balance": -13.0},
            {"account_id": self.account_stock_transit.id, "balance": 13.0},
        ])
        self.assertAlmostEqual(self._posted_balance(self.account_stock_transit), 0.0)

    # ------------------------------------------------------------------
    # Accrual / delivered-not-invoiced exclusion
    # ------------------------------------------------------------------

    def test_transit_delivery_excluded_from_accrual_list(self):
        so = self._stock_and_deliver(self.product_delivery)
        line = so.order_line
        self.assertTrue(line._has_goods_in_transit_entry())
        self.assertNotIn(
            line,
            self.env["sale.order.line"].search([
                ("invoice_to_be_issued", "=", True),
            ]),
        )
        candidates = self.company._get_accrual_candidate_lines()
        self.assertNotIn(
            line,
            candidates.get("invoice_to_be_issued", self.env["sale.order.line"]),
        )

    def test_transit_delivery_excluded_from_accrual_wizard(self):
        so = self._stock_and_deliver(self.product_delivery)
        line = so.order_line
        wizard = self.env["account.accrued.orders.wizard"].with_context(
            active_model="sale.order.line",
            active_ids=line.ids,
            default_accrual_type="invoice_to_be_issued",
        ).create({"date": fields.Date.today()})

        main_vals, __ = wizard._get_accrual_main_line_vals(
            line, fields.Date.today()
        )
        cogs_vals, counterpart_vals = wizard._get_accrual_pending_cogs_vals(
            line, fields.Date.today()
        )
        self.assertFalse(main_vals)
        self.assertFalse(cogs_vals)
        self.assertFalse(counterpart_vals)

    def test_transit_delivery_excluded_from_stock_valuation_report(self):
        self._stock_and_deliver(self.product_delivery)
        report_data = self.env["account.stock.valuation.report"].with_company(
            self.company
        )._get_report_data()
        self.assertNotIn("accrual", report_data)

    def test_periodic_delivery_still_in_accrual_list(self):
        self._make_in_move(
            self.product_standard, 1, self.product_standard.standard_price
        )
        so = self._so_deliver(
            self.product_standard, quantity=1, price=20.0, partner=self.customer
        )
        line = so.order_line
        self.assertFalse(line._has_goods_in_transit_entry())
        self.assertIn(
            line,
            self.env["sale.order.line"].search([
                ("invoice_to_be_issued", "=", True),
            ]),
        )

    def _deliver_invoice_return(self, product=None):
        product = product or self.product_delivery
        so = self._stock_and_deliver(product)
        invoice = so._create_invoices()
        invoice.action_post()
        self._make_return(so.picking_ids.move_ids, 1)
        return so, invoice

    def _intercompany_transit(self):
        return self.env.ref("stock.stock_location_inter_company")

    def _create_intercompany_delivery(self, product=None, quantity=1, price=66.0):
        """Simulate the selling company's intercompany delivery leg:
        internal stock -> global Inter-company transit location."""
        product = product or self.product_delivery
        self._make_in_move(product, quantity, product.standard_price)
        so = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "order_line": [Command.create({
                "product_id": product.id,
                "product_uom_qty": quantity,
                "price_unit": price,
                "tax_ids": False,
            })],
        })
        so.action_confirm()
        picking = so.picking_ids
        intercompany = self._intercompany_transit()
        picking.location_dest_id = intercompany.id
        move = picking.move_ids
        move.move_line_ids.unlink()
        move.location_dest_id = intercompany.id
        move._action_assign()
        move.write({"quantity": quantity, "picked": True})
        picking.with_context(skip_backorder=True).button_validate()
        return so, picking.move_ids

    def test_return_excluded_from_invoiced_not_delivered_list(self):
        so, __ = self._deliver_invoice_return()
        line = so.order_line
        self.assertTrue(line._has_goods_in_transit_return())
        self.assertNotIn(
            line,
            self.env["sale.order.line"].search([
                ("deferred_revenue", "=", True),
            ]),
        )
        candidates = self.company._get_accrual_candidate_lines()
        self.assertNotIn(
            line,
            candidates.get("invoiced_not_delivered", self.env["sale.order.line"]),
        )

    def test_return_excluded_from_accrual_wizard(self):
        so, __ = self._deliver_invoice_return()
        line = so.order_line
        wizard = self.env["account.accrued.orders.wizard"].with_context(
            active_model="sale.order.line",
            active_ids=line.ids,
            default_accrual_type="invoiced_not_delivered",
        ).create({"date": fields.Date.today()})

        main_vals, __ = wizard._get_accrual_main_line_vals(
            line, fields.Date.today()
        )
        cogs_vals, counterpart_vals = wizard._get_accrual_pending_cogs_vals(
            line, fields.Date.today()
        )
        self.assertFalse(main_vals)
        self.assertFalse(cogs_vals)
        self.assertFalse(counterpart_vals)

    def test_return_excluded_from_stock_valuation_report(self):
        self._deliver_invoice_return()
        report_data = self.env["account.stock.valuation.report"].with_company(
            self.company
        )._get_report_data()
        self.assertNotIn("accrual", report_data)

    def test_intercompany_delivery_creates_transit_entry(self):
        so, delivery_move = self._create_intercompany_delivery()
        entry = delivery_move.account_move_id
        self.assertTrue(entry)
        self.assertRecordValues(entry.line_ids.sorted("balance"), [
            {
                "account_id": self.account_stock_valuation.id,
                "balance": -42.0,
            },
            {
                "account_id": self.account_stock_transit.id,
                "balance": 42.0,
            },
        ])

        line = so.order_line
        self.assertTrue(line._has_goods_in_transit_entry())
        self.assertNotIn(
            line,
            self.env["sale.order.line"].search([
                ("invoice_to_be_issued", "=", True),
            ]),
        )
        report_data = self.env["account.stock.valuation.report"].with_company(
            self.company
        )._get_report_data()
        self.assertNotIn("accrual", report_data)

        invoice = so._create_invoices()
        invoice.action_post()
        cogs = invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertRecordValues(cogs.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -42.0},
            {"account_id": self.account_expense.id, "balance": 42.0},
        ])
        self.assertAlmostEqual(self._posted_balance(self.account_stock_transit), 0.0)

    def test_intercompany_receipt_does_not_create_transit_entry(self):
        move = self.env["stock.move"].create({
            "product_id": self.product_delivery.id,
            "location_id": self._intercompany_transit().id,
            "location_dest_id": self.stock_location.id,
            "product_uom_qty": 1,
            "picking_type_id": self.picking_type_in.id,
        })
        move._action_confirm()
        move._action_assign()
        move.write({"quantity": 1, "picked": True})
        move._action_done()

        self.assertFalse(move.sale_line_id)
        self.assertFalse(move.account_move_id)

    def test_intercompany_purchase_return_mirror_excluded_from_sales_accrual(self):
        self._make_in_move(
            self.product_delivery, 1, self.product_delivery.standard_price
        )
        so = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "order_line": [Command.create({
                "product_id": self.product_delivery.id,
                "product_uom_qty": 1,
                "price_unit": 66.0,
                "tax_ids": False,
            })],
        })
        so.action_confirm()

        purchase = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "order_line": [Command.create({
                "product_id": self.product_delivery.id,
                "product_qty": 1,
                "price_unit": 42.0,
                "tax_ids": [Command.clear()],
            })],
        })
        purchase.button_confirm()

        picking = so.picking_ids
        intercompany = self._intercompany_transit()
        picking.location_dest_id = intercompany.id
        move = picking.move_ids
        move.write({"purchase_line_id": purchase.order_line.id})
        move.move_line_ids.unlink()
        move.location_dest_id = intercompany.id
        move._action_assign()
        move.write({"quantity": 1, "picked": True})
        picking.with_context(skip_backorder=True).button_validate()

        # A purchase return must not create a sales transit entry.
        self.assertFalse(move.account_move_id)

        line = so.order_line
        self.assertTrue(line._has_intercompany_purchase_return())
        self.assertNotIn(
            line,
            self.env["sale.order.line"].search([
                ("invoice_to_be_issued", "=", True),
            ]),
        )
        candidates = self.company._get_accrual_candidate_lines()
        self.assertNotIn(
            line,
            candidates.get("invoice_to_be_issued", self.env["sale.order.line"]),
        )

    def test_intercompany_refund_input_vat_storno(self):
        self.company.account_storno = True
        tax = self.env["account.tax"].sudo().search([
            ("company_id", "=", self.company.id),
            ("type_tax_use", "=", "purchase"),
        ], limit=1)
        self.assertTrue(tax, "No purchase tax configured for the test company")

        move = self.env["account.move"].create({
            "move_type": "in_refund",
            "partner_id": self.vendor.id,
            "auto_generated": True,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [Command.create({
                "product_id": self.product_standard.id,
                "quantity": 1.0,
                "price_unit": 100.0,
                "tax_ids": [Command.set(tax.ids)],
            })],
        })
        move.action_post()

        tax_lines = move.line_ids.filtered(
            lambda line: line.display_type in ("tax", "non_deductible_tax")
        )
        self.assertTrue(tax_lines)
        for line in tax_lines:
            self.assertTrue(line.is_storno)
            if line.balance < 0:
                self.assertAlmostEqual(line.debit, line.balance)
                self.assertAlmostEqual(line.credit, 0.0)
            else:
                self.assertAlmostEqual(line.debit, 0.0)
                self.assertAlmostEqual(line.credit, -line.balance)

        # Force the buggy state and verify the corrective helper.
        line = tax_lines[0]
        if line.balance < 0:
            line.sudo().with_context(check_move_validity=False).write({
                "is_storno": False,
                "debit": 0.0,
                "credit": -line.balance,
            })
            self.assertFalse(line.is_storno)
            move._fix_intercompany_refund_storno()
            self.assertTrue(line.is_storno)
            self.assertAlmostEqual(line.debit, line.balance)
            self.assertAlmostEqual(line.credit, 0.0)

    def test_intercompany_return_creates_reverse_entry(self):
        so, delivery_move = self._create_intercompany_delivery()
        invoice = so._create_invoices()
        invoice.action_post()

        return_moves = self._make_return(delivery_move, 1)
        return_move = return_moves
        entry = return_move.account_move_id
        self.assertTrue(entry)
        self.assertRecordValues(entry.line_ids.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -42.0},
            {"account_id": self.account_stock_valuation.id, "balance": 42.0},
        ])

        line = so.order_line
        line.invalidate_recordset()
        self.assertTrue(line._has_goods_in_transit_return())
        self.assertNotIn(
            line,
            self.env["sale.order.line"].search([
                ("deferred_revenue", "=", True),
            ]),
        )

    def test_partial_delivery_without_return_still_in_invoiced_not_delivered(self):
        self._make_in_move(
            self.product_order, 2, self.product_order.standard_price
        )
        so = self.env["sale.order"].create({
            "partner_id": self.customer.id,
            "warehouse_id": self.warehouse.id,
            "order_line": [Command.create({
                "product_id": self.product_order.id,
                "product_uom_qty": 2,
                "price_unit": 66.0,
                "tax_ids": False,
            })],
        })
        so.action_confirm()
        invoice = so._create_invoices()
        invoice.action_post()

        picking = so.picking_ids
        picking.move_ids.write({"quantity": 1, "picked": True})
        picking.with_context(skip_backorder=True).button_validate()

        line = so.order_line
        self.assertTrue(line._has_goods_in_transit_entry())
        self.assertFalse(line._has_goods_in_transit_return())
        self.assertIn(
            line,
            self.env["sale.order.line"].search([
                ("deferred_revenue", "=", True),
            ]),
        )

    # ------------------------------------------------------------------
    # Out-of-scope flows
    # ------------------------------------------------------------------

    def test_periodic_untouched(self):
        self._make_in_move(self.product_standard, 1, self.product_standard.standard_price)
        so = self._so_deliver(
            self.product_standard, quantity=1, price=20.0, partner=self.customer
        )
        self.assertFalse(so.picking_ids.move_ids.account_move_id)

        invoice = so._create_invoices()
        invoice.action_post()
        self.assertFalse(
            invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        )

    def test_manual_and_dropship_excluded(self):
        self._make_in_move(self.product_delivery, 1, self.product_delivery.standard_price)

        manual = self._make_out_move(self.product_delivery, 1)
        self.assertFalse(manual.sale_line_id)
        self.assertFalse(manual.account_move_id)

        dropship = self._make_dropship_move(self.product_delivery, 1, unit_cost=42)
        self.assertTrue(dropship.is_dropship)
        self.assertFalse(dropship.account_move_id)

        self.assertAlmostEqual(self._posted_balance(self.account_stock_transit), 0.0)

    def test_missing_transit_account_blocks_delivery(self):
        self.company.account_stock_transit_id = False
        self.category_standard_auto.with_company(
            self.company
        ).property_stock_account_transit_id = False
        self._make_in_move(self.product_delivery, 1, self.product_delivery.standard_price)

        with self.assertRaisesRegex(UserError, "Goods in Transit"):
            self._so_deliver(
                self.product_delivery, quantity=1, price=66.0, partner=self.customer
            )

    def test_missing_transit_account_blocks_invoice(self):
        self.company.account_stock_transit_id = False
        self.category_standard_auto.with_company(
            self.company
        ).property_stock_account_transit_id = False
        so = self._so_deliver(
            self.product_order, quantity=1, price=66.0,
            partner=self.customer, picking=False,
        )
        invoice = so._create_invoices()
        with self.assertRaisesRegex(UserError, "Goods in Transit"):
            invoice.action_post()

    # ------------------------------------------------------------------
    # COGS revaluation and multi-company
    # ------------------------------------------------------------------

    def test_set_cogs_updates_transit_side(self):
        so = self._stock_and_deliver(self.product_delivery)
        invoice = so._create_invoices()
        invoice.action_post()
        delivery_move = so.picking_ids.move_ids
        delivery_move.write({"value": -52.0})

        cogs = invoice.line_ids.filtered(lambda line: line.display_type == "cogs")
        self.assertRecordValues(cogs.sorted("balance"), [
            {"account_id": self.account_stock_transit.id, "balance": -52.0},
            {"account_id": self.account_expense.id, "balance": 52.0},
        ])

    def test_multicompany_account_resolution(self):
        other_company = self.other_company
        other_transit = self.env["account.account"].with_company(other_company).create({
            "name": "Goods in Transit Other",
            "code": "110598",
            "account_type": "asset_current",
        })
        other_company.account_stock_transit_id = other_transit

        template = self.product_delivery.product_tmpl_id
        self.assertEqual(
            template.with_company(other_company)._get_product_accounts()["stock_transit"],
            other_transit,
        )
        self.assertEqual(
            template.with_company(self.company)._get_product_accounts()["stock_transit"],
            self.account_stock_transit,
        )
