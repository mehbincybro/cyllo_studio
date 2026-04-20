# -*- coding: utf-8 -*-
{
    'name': 'Warranty Repair',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': "Warranty status integration for Repair Orders",
    'description': """This module integrates warranty status into repair orders, 
linking them to sale order lines.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_warranty_sale', 'repair'],
    'data': [
        'views/repair_order_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
