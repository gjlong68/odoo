# -*- coding: utf-8 -*-
{  # noqa: B018 - Odoo manifest is a bare dict expression

    'name': "zd_production_account",

    'summary': """
        在产品成本的处理
        """,

    'description': """
        1)、查询未完工的生产订单\n
        2)、根据未完工的生产订单查询在产品材料成本并重分类处理\n
        下期冲回\n
        3)、在成本计算表中扣除在产品耗用的材料成本\n
        注：需要手动填入，通过增加production_id建立与生产单(production order)关联，
        通过生产单的状态(State)确认在产品和完工产品的成本和完工时间(End Date)，需要二次开发。\n

    """,

    'author': "广州众谛信息科技有限公司",
    'website': "https://www.zodioo.com/",
    'category': 'account',
    'version': '20.0.1.0.0',
    'depends': ['mrp_account', 'stock_account'],
    'license': 'OPL-1',
    'data': [
        'views/zd_view_account_analytic_line_form.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
