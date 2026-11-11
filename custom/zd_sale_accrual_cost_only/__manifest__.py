# Part of Sales Accrual Cost Only. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': 'Sales Accrual Cost Only',
    'version': '20.0.1.0.2',
    'category': 'Accounting/Accounting',
    'summary': 'Post only the cost side of delivered-not-invoiced sales accruals',
    'description': """
Sales Accrual Cost Only
=======================

Odoo's accrued-orders wizard posts two pairs of journal items for a sale
order line whose delivered and invoiced quantities differ:

* revenue: ``Dr Invoices to be Issued / Cr Income``;
* cost: ``Dr Expense / Cr Stock Valuation``.

This module keeps only the cost side and posts it as a balance-sheet
reclassification between the "Invoices to be Issued" account and the stock
valuation account (``Dr Invoices to be Issued / Cr Stock Valuation``).  The
automatic reversal created by the wizard mirrors those two lines.

All sale lines are affected: periodic-valued products and services no longer
produce a revenue accrual (they have no cost side to reclassify).  Purchase
accruals are unchanged.

The mirrored sale line of an intercompany purchase return is excluded from
the sales accrual: its cost is already accrued on the purchase side
(``bills to receive`` / ``billed not received``).  The return move is also
kept out of the sale order's transfers: it is a purchase return, not a sale
delivery, and must not create a sale order line or a ``sale_line_id``.

Finally, tax lines of auto-generated inter-company refunds are normalized to
storno presentation (negative debit instead of a positive opposite-side
amount) when the company uses storno accounting.
    """,
    'author': '广州众谛信息科技有限公司',
    'website': 'https://www.zodioo.com/',
    'license': 'OPL-1',
    'depends': ['base', 'sale_stock', 'purchase_stock', 'stock_account'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
