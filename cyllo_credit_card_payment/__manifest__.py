# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Credit Card Payment',
    'version': "1.0.0",
    'category': 'Accounting',
    'summary': """Credit Card Payment""",
    'description': "Added credit card payment option",
    'license': 'LGPL-3',
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['base', 'account'],
    'data': [
        'data/account_payment_data.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    "post_init_hook": "add_payment_method"
}
