# -*- coding: utf-8 -*-
{
    'name': 'Warranty Purchase',
    'version': '1.0.0',
    'category': 'Purchase',
    'summary': "Warranty features for Purchases and Stock",
    'description': """This module adds warranty tracking to purchase order lines and 
propagates it to receipts.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_warranty_base', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/warranty_extension_wizard_views.xml',
        'views/purchase_order_line_views.xml',
        'views/stock_move_line_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
