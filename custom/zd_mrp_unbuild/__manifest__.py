# -*- coding: utf-8 -*-
{  # noqa: B018 - Odoo manifest is a bare dict expression
    'name': "zd_mrp_unbuild",

    'summary': """
        处理分解单完成后，不生成对应的分析项目，就是生产单生成分析项目的你过程
        """,

    'description': """
        处理分解单完成后，不生成对应的分析项目，就是生产单生成分析项目的你过程

    """,

    'author': "广州众谛信息科技有限公司",
    'website': "https://www.zodioo.com/",
    'category': 'account',
    'version': '20.0.1.0.1',
    'depends': ['mrp_account', 'analytic', 'project_mrp_account', 'zd_production_account'],
    'license': 'OPL-1',
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
