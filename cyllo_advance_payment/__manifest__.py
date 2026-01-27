# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Advance Payment',
    'version': '1.0.0',
    'summary': """Advance Payment for Sales And Purchase""",
    'description': "Advance payment option on sales and purchase",
    'license': 'LGPL-3',
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['sale_management', 'purchase', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'wizards/advance_payment_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
