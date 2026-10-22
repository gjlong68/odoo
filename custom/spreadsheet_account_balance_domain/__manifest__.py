# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': "Spreadsheet Account Balance Domain",
    'version': '20.0.1.0.0',
    'category': 'Accounting',
    'summary': 'ODOO.BALANCE.TAG spreadsheet formula with an optional account.move.line domain',
    'description': """
Extends the Odoo 20 ODOO.BALANCE.TAG() spreadsheet formula with an optional
sixth argument: a JSON-encoded Odoo domain over account.move.line.

Formula::

    ODOO.BALANCE.TAG(account_tag_ids, date_range, [offset], [company_id],
                     [include_unposted], [domain])

The extra domain is ANDed with the standard tag/date/company/posted domain.
Date semantics: "21/12/2022" is an end date (balance up to that date), while
"Q1/2022", "12/2022" and "2022" are periods (movements within the period).
The same rule applies to every account type.

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
