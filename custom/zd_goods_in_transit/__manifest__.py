# Part of Goods in Transit. See LICENSE file for full copyright and licensing details.
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': 'Goods in Transit',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Goods in Transit accounting for sale deliveries, invoices, returns and refunds',
    'description': """
Posts sale-order deliveries of real-time-valued products to a Goods in Transit
account (Dr Goods in Transit / Cr Stock Valuation), routes invoice COGS through
transit (Dr COGS / Cr Goods in Transit), and reverses both on returns and credit
notes. Periodic-valuation products and native stock valuation are unchanged.
    """,
    'author': '广州众谛信息科技有限公司',
    'website': 'https://www.zodioo.com/',
    'license': 'OPL-1',
    'depends': [
        'base',
        'sale_stock',
        'purchase_stock',
        'stock_account',
        'account_accountant',
        'account_inter_company_rules',
    ],
    'data': [
        'views/product_category_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
