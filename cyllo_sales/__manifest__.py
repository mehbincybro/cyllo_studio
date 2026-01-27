# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Merge Quotation',
    'version': '1.0.0',
    'category': 'Sales ',
    'summary': """This module merge two or more Quotation""",
    'description': """Cyllo Merge Quotation is a module that allows users to 
     merge multiple quotations into a single one by deleting the others""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management'],
    'data': [
        'data/ir_actions_server_data.xml',
        'views/sale_order_discount_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
