# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Base Partner',
    'version': "1.0.0",
    'summary': 'Choose customer and vendor',
    'description': 'Option for recognizing between customer and vendor',
    'category': 'Warehouse',
    'author': 'Cyllo',
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['contacts', 'sale_management', 'purchase', 'account'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_management_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'images': [''],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True
}
