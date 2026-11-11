# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.

from unittest import SkipTest

from odoo import fields
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleAccrualCostOnly(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module'].search([
            ('name', '=', 'zd_goods_in_transit'),
            ('state', '=', 'installed'),
        ], limit=1):
            raise SkipTest(
                "zd_goods_in_transit is installed and filters sale accruals; "
                "run these tests in a database where it is uninstalled."
            )
        cls.company = cls.env.company

        Account = cls.env['account.account']
        cls.stock_valuation_account = Account.create({
            'code': 'ZD140501',
            'name': 'Stock Valuation (test)',
            'account_type': 'asset_current',
        })
        cls.invoices_to_issue_account = Account.create({
            'code': 'ZD140601',
            'name': 'Invoices to be Issued (test)',
            'account_type': 'asset_current',
        })
        cls.invoiced_not_delivered_account = Account.create({
            'code': 'ZD220501',
            'name': 'Invoiced not Delivered (test)',
            'account_type': 'liability_current',
        })
        cls.income_account = Account.create({
            'code': 'ZD600101',
            'name': 'Income (test)',
            'account_type': 'income',
        })
        cls.expense_account = Account.create({
            'code': 'ZD640101',
            'name': 'Expense (test)',
            'account_type': 'expense_direct_cost',
        })

        cls.category = cls.env['product.category'].create({
            'name': 'Sale Accrual Cost Only Category',
            'property_valuation': 'real_time',
            'property_cost_method': 'standard',
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_account_invoices_to_issue_id': cls.invoices_to_issue_account.id,
            'property_account_invoiced_not_delivered_id': cls.invoiced_not_delivered_account.id,
            'property_account_income_categ_id': cls.income_account.id,
            'property_account_expense_categ_id': cls.expense_account.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Sale Accrual Cost Only Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': cls.category.id,
            'standard_price': 100.0,
            'list_price': 100.0,
        })

        # The closing action needs a stock journal and a company-level valuation
        # account when it has closing lines to create.
        cls.company.account_stock_journal_id = cls.company_data['default_journal_misc']
        cls.company.account_stock_valuation_id = cls.stock_valuation_account

    def _create_sale_order(self, product=None, qty=10.0):
        product = product or self.product
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': product.list_price,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()
        return sale_order

    def _deliver(self, sale_order, qty):
        pickings = sale_order.picking_ids.filtered(
            lambda picking: picking.state not in ('done', 'cancel')
        )
        pickings.move_ids.write({'quantity': qty, 'picked': True})
        result = pickings.button_validate()
        if isinstance(result, dict):
            Form.from_action(self.env, result).save().process()

    def _invoice(self, sale_order):
        invoice = sale_order._create_invoices()
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        return invoice

    def _create_purchase_line(self):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_qty': 5.0,
                'price_unit': 100.0,
                'tax_ids': False,
            })],
        })
        return purchase_order.order_line

    def _make_intercompany_purchase_return_line(self):
        """Turn a delivered sale line into a mirror of an intercompany purchase return.

        The return move leaves company stock for the global inter-company
        transit location and is linked to both the purchase line and the
        mirrored sale line.
        """
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)
        purchase_line = self._create_purchase_line()
        move = sale_order.picking_ids.move_ids.filtered(
            lambda stock_move: stock_move.state == 'done'
        )
        move.write({
            'purchase_line_id': purchase_line.id,
            'location_dest_id': self.env.ref('stock.stock_location_inter_company').id,
        })
        return sale_order.order_line

    def _create_accrual_wizard(self, order_lines, accrual_type):
        return self.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order.line',
            'active_ids': order_lines.ids,
            'default_accrual_type': accrual_type,
        }).create({
            'date': fields.Date.today(),
        })

    def _get_accrual_moves(self, action):
        moves = self.env['account.move'].search(action['domain'])
        return (
            moves.filtered(lambda move: not move.reversed_entry_id),
            moves.filtered(lambda move: move.reversed_entry_id),
        )

    def _assert_cost_pair(self, move, debit_account, credit_account, amount):
        self.assertEqual(len(move.line_ids), 2)
        debit_lines = move.line_ids.filtered(lambda line: line.debit)
        credit_lines = move.line_ids.filtered(lambda line: line.credit)
        self.assertEqual(len(debit_lines), 1)
        self.assertEqual(len(credit_lines), 1)
        self.assertEqual(debit_lines.account_id, debit_account)
        self.assertAlmostEqual(debit_lines.debit, amount)
        self.assertEqual(credit_lines.account_id, credit_account)
        self.assertAlmostEqual(credit_lines.credit, amount)
        self.assertEqual(set(move.line_ids.mapped('display_type')), {'product'})

    def test_invoice_to_be_issued_cost_only(self):
        """Delivered-not-invoiced accrual posts only the cost reclassification."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)

        action = self._create_accrual_wizard(
            sale_order.order_line, 'invoice_to_be_issued',
        ).create_entries()
        original_moves, reversal_moves = self._get_accrual_moves(action)
        self.assertEqual(len(original_moves), 1)
        self.assertEqual(len(reversal_moves), 1)

        self._assert_cost_pair(
            original_moves,
            self.invoices_to_issue_account,
            self.stock_valuation_account,
            500.0,
        )
        self._assert_cost_pair(
            reversal_moves,
            self.stock_valuation_account,
            self.invoices_to_issue_account,
            500.0,
        )

    def test_invoiced_not_delivered_cost_only(self):
        """Invoiced-not-delivered accrual posts only the cost reclassification."""
        self.product.invoice_policy = 'order'
        sale_order = self._create_sale_order()
        self._invoice(sale_order)
        self._deliver(sale_order, 5)

        action = self._create_accrual_wizard(
            sale_order.order_line, 'invoiced_not_delivered',
        ).create_entries()
        original_moves, reversal_moves = self._get_accrual_moves(action)
        self.assertEqual(len(original_moves), 1)
        self.assertEqual(len(reversal_moves), 1)

        self._assert_cost_pair(
            original_moves,
            self.stock_valuation_account,
            self.invoiced_not_delivered_account,
            500.0,
        )
        self._assert_cost_pair(
            reversal_moves,
            self.invoiced_not_delivered_account,
            self.stock_valuation_account,
            500.0,
        )

    def test_report_accrual_shows_cost_only(self):
        """The inventory valuation report preview exposes no revenue account."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)

        report = self.env['account.stock.valuation.report'].with_company(self.company)
        report_data = report._get_report_data()

        self.assertIn('accrual', report_data)
        accrual_lines = [
            (line.get('accrual_type'), sub_line['account_id'],
             sub_line['debit'], sub_line['credit'])
            for line in report_data['accrual']['lines']
            for sub_line in line['lines']
        ]
        self.assertIn(
            ('invoice_to_be_issued', self.invoices_to_issue_account.id, 500.0, 0.0),
            accrual_lines,
        )
        self.assertIn(
            (None, self.stock_valuation_account.id, 0.0, 500.0),
            accrual_lines,
        )
        account_ids = {sub_line[1] for sub_line in accrual_lines}
        self.assertNotIn(self.income_account.id, account_ids)
        self.assertNotIn(self.expense_account.id, account_ids)

    def test_close_stock_valuation_accrual_cost_only(self):
        """The report's Generate Entries button produces the same cost-only accrual."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)

        action = self.company.action_close_stock_valuation(
            include_accruals=True, auto_post=True,
        )
        moves = self.env['account.move'].search(action['domain'])
        accrual_moves = moves.filtered(
            lambda move: not move.reversed_entry_id
            and move.line_ids.filtered(
                lambda line: line.account_id == self.invoices_to_issue_account
            )
        )
        self.assertEqual(len(accrual_moves), 1)
        self._assert_cost_pair(
            accrual_moves,
            self.invoices_to_issue_account,
            self.stock_valuation_account,
            500.0,
        )

        reversal_moves = moves.filtered(
            lambda move: move.reversed_entry_id == accrual_moves
        )
        self.assertEqual(len(reversal_moves), 1)
        self._assert_cost_pair(
            reversal_moves,
            self.stock_valuation_account,
            self.invoices_to_issue_account,
            500.0,
        )

    def test_manual_amount_rejected_for_sales(self):
        """Sales accruals cannot be forced with the wizard's manual amount."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)

        wizard = self._create_accrual_wizard(
            sale_order.order_line, 'invoice_to_be_issued',
        )
        wizard.amount = 100.0
        with self.assertRaises(UserError):
            wizard.create_entries()

    def test_intercompany_purchase_return_line_is_excluded(self):
        """The mirrored sale line of an intercompany purchase return is not accrued."""
        sale_line = self._make_intercompany_purchase_return_line()
        self.assertTrue(sale_line._is_intercompany_purchase_return_line())
        self.assertNotIn(
            sale_line,
            self.env['sale.order.line']._get_accrual_line_ids(mode='invoice_issued'),
        )

        report_data = self.env['account.stock.valuation.report'].with_company(
            self.company,
        )._get_report_data()
        self.assertNotIn('accrual', report_data)

        wizard = self._create_accrual_wizard(sale_line, 'invoice_to_be_issued')
        with self.assertRaises(UserError):
            wizard.create_entries()

    def test_intercompany_refund_input_vat_storno(self):
        """Auto-generated refunds present input VAT as a negative debit under Storno."""
        self.company.account_storno = True
        tax = self.tax_purchase_a
        self.assertTrue(tax, "No purchase tax configured for the test company")
        vendor = self.env['res.partner'].create({
            'name': 'Storno Vendor',
            'supplier_rank': 1,
        })

        move = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': vendor.id,
            'auto_generated': True,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1.0,
                'price_unit': 100.0,
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        move.action_post()

        tax_lines = move.line_ids.filtered(
            lambda line: line.display_type in ('tax', 'non_deductible_tax')
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
                'is_storno': False,
                'debit': 0.0,
                'credit': -line.balance,
            })
            self.assertFalse(line.is_storno)
            move._fix_intercompany_refund_storno()
            self.assertTrue(line.is_storno)
            self.assertAlmostEqual(line.debit, line.balance)
            self.assertAlmostEqual(line.credit, 0.0)

    def test_intercompany_purchase_return_does_not_create_sale_line(self):
        """Stock validation cannot create a sale line for a purchase return move."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)
        purchase_line = self._create_purchase_line()
        move = sale_order.picking_ids.move_ids.filtered(
            lambda stock_move: stock_move.state == 'done'
        )
        move.write({
            'purchase_line_id': purchase_line.id,
            'location_dest_id': self.env.ref('stock.stock_location_inter_company').id,
            'sale_line_id': False,
        })

        sale_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
            'product_uom_qty': 0.0,
            'qty_delivered': 5.0,
            'product_uom_id': self.product.uom_id.id,
            'move_ids': [Command.link(move.id)],
        })
        self.assertFalse(sale_line)

    def test_normal_sale_line_is_not_excluded(self):
        """A regular delivered-not-invoiced sale line remains eligible for accrual."""
        sale_order = self._create_sale_order()
        self._deliver(sale_order, 5)
        self.assertFalse(sale_order.order_line._is_intercompany_purchase_return_line())
        self.assertIn(
            sale_order.order_line,
            self.env['sale.order.line']._get_accrual_line_ids(mode='invoice_issued'),
        )

    def test_periodic_product_has_no_accrual(self):
        """Periodic products have no cost side, so no sales accrual is generated."""
        periodic_category = self.env['product.category'].create({
            'name': 'Periodic Sale Accrual Category',
            'property_valuation': 'periodic',
            'property_cost_method': 'standard',
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_account_income_categ_id': self.income_account.id,
            'property_account_expense_categ_id': self.expense_account.id,
        })
        periodic_product = self.env['product.product'].create({
            'name': 'Periodic Sale Accrual Product',
            'type': 'consu',
            'is_storable': True,
            'categ_id': periodic_category.id,
            'standard_price': 100.0,
            'list_price': 100.0,
        })
        sale_order = self._create_sale_order(product=periodic_product)
        self._deliver(sale_order, 5)

        report = self.env['account.stock.valuation.report'].with_company(self.company)
        self.assertNotIn('accrual', report._get_report_data())

        wizard = self._create_accrual_wizard(
            sale_order.order_line, 'invoice_to_be_issued',
        )
        with self.assertRaises(UserError):
            wizard.create_entries()
