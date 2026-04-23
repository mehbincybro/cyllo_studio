# -*- coding: utf-8 -*-
{
    'name': 'Warranty Base',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': "Foundational warranty features",
    'description': """This module provides the base fields and logic for the warranty system, 
including warranty periods on products and categories.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['product'],
    'data': [
        'views/product_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
