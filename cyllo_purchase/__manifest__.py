# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Merge RFQ',
    'version': '1.0.0',
    'category': 'Sales ',
    'summary': """This module merge two or more RFQ""",
    'description': """Cyllo Merge RFQ is a module that allows users to 
     merge multiple RFQ into a single one by deleting the others""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['purchase'],
    'data': [
        'views/merge_rfq_action.xml',
        'views/purchase_order_view.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}