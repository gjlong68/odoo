# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': "Spreadsheet Account Balance Domain",
    'version': '20.0.1.0.0',
    'category': 'Accounting',
    'summary': 'ODOO.BALANCE and ODOO.BALANCE.TAG with an optional account.move.line domain',
    'description': """
Adds optional arguments to the ODOO.BALANCE() and ODOO.BALANCE.TAG()
spreadsheet formulas: a JSON-encoded Odoo domain over account.move.line,
and, for ODOO.BALANCE.TAG, tax tag ids.

Formulas::

    ODOO.BALANCE(account_codes, date_range, [offset], [company_id],
                 [include_unposted], [domain])
    ODOO.BALANCE.TAG(account_tag_ids, date_range, [offset], [company_id],
                     [include_unposted], [domain], [tax_tag_ids])

The extra domain is ANDed with the standard account/date/company/posted domain.
For ODOO.BALANCE.TAG, tax_tag_ids filters account.move.line.tax_tag_ids, is
ANDed with account tags, and can be used without any account tag.

ODOO.BALANCE keeps the core Odoo 20 date semantics. ODOO.BALANCE.TAG uses:
"21/12/2022" is an end date (balance up to that date), while "Q1/2022",
"12/2022" and "2022" are periods (movements within the period), applied to
every account type.

Note: the "See records" cell action does not include the optional domain.
    """,
    'depends': ['spreadsheet', 'spreadsheet_account', 'account'],
    'installable': True,
    'auto_install': False,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [],
    'assets': {
        'spreadsheet.o_spreadsheet_core': [
            'spreadsheet_account_balance_domain/static/src/**/*.js',
        ],
    },
}
