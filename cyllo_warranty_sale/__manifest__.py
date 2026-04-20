# -*- coding: utf-8 -*-
{
    'name': 'Warranty Sale',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': "Warranty features for Sales and Stock",
    'description': """This module adds warranty tracking to sale order lines and 
propagates it to delivery orders.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_warranty_base', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/warranty_extension_wizard_views.xml',
        'views/sale_order_line_views.xml',
        'views/stock_move_line_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
