# -*- coding: utf-8 -*-
{
    'name': "Cyllo Web",
    'version': '1.0.0',
    'website': "https://www.cyllo.com",
    'summary': 'Module to change UI of login page and database manager',
    'description': """This module facilitates the alteration of the user interface (UI) and user experience (UX) 
    for various components, including the login page, password reset functionality, sign-up page, and database 
    manager""",
    'category': 'Hidden',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['cyllo_base', 'base'],
    'assets': {
        'web.assets_frontend': [
            'cyllo_web/static/src/css/style.css',
        ],
    },
    'data': [
        'views/auth_signup_fields.xml',
        'views/login_templates.xml',
        'views/auth_signup_login_templates.xml',
        'views/webclient_templates.xml',
    ],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': True,
    'application': False,
}
