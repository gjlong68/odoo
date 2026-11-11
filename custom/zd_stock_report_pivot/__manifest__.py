# Part of Stock Report Pivot. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': 'Stock Report Pivot',
    'version': '20.0.1.2.0',
    'category': 'Supply Chain/Inventory',
    'summary': 'Pivot views, Stock by Company and Inventory at Date reports',
    'description': (
        'Adds a pivot view and an Inventory at Date report to Inventory > Reporting > Stock, '
        'plus a Stock by Company pivot/list report grouped by inventory company and product category.'
    ),
    'author': '广州众谛信息科技有限公司',
    'website': 'https://www.zodioo.com/',
    'license': 'OPL-1',
    'depends': ['stock'],
    'data': [
        'security/ir.access.csv',
        'wizard/inventory_at_date_views.xml',
        'views/product_views.xml',
        'views/stock_company_report_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zd_stock_report_pivot/static/src/stock_report_search_panel_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
