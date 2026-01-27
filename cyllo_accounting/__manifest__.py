# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Accounting',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': """Accounting Customizations""",
    'description': "More functionalities on accounting module",
    'license': 'LGPL-3',
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['web', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/account_asset_modify_views.xml',
        'views/account_payment_views.xml',
        'views/account_asset_type_views.xml',
        'views/account_move_views.xml',
        'views/account_asset_views.xml',
        'views/cyllo_accounting_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_accounting/static/src/js/relational_utils.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
