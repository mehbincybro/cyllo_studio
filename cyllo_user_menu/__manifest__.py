# -*- coding: utf-8 -*-
{
    'name': "Cyllo User Menu",
    'version': '1.0.0',
    'summary': """Module to change design of user menu""",
    'description': "This module helps to change UI design and its corresponding functionalities of user menu",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base'],
    'assets': {
        'web.assets_backend': [
            "cyllo_user_menu/static/src/xml/user_menu.xml",
            "cyllo_user_menu/static/src/css/style.scss",
            "cyllo_user_menu/static/src/js/user_menu.js",
        ]
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True
}
