# Part of Stock Report Pivot. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': 'Stock Report Pivot',
    'version': '20.0.1.1.0',
    'category': 'Supply Chain/Inventory',
    'summary': 'Pivot view and Inventory at Date report for the Inventory Stock report',
    'description': 'Adds a pivot view and an Inventory at Date report to Inventory > Reporting > Stock.',
    'author': '广州众谛信息科技有限公司',
    'website': 'https://www.zodioo.com/',
    'license': 'OPL-1',
    'depends': ['stock'],
    'data': [
        'security/ir.access.csv',
        'wizard/inventory_at_date_views.xml',
        'views/product_views.xml',
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
