# -*- coding: utf-8 -*-

{
    'name': 'App Mass Install',
    'summary': """Onboarding view after login for the first time""",
    'version': '1.0',
    'description': "This module gives Onboarding view after login for the first time",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web', 'base'],
    'data': [
        'views/massive_app_install_templates.xml',
        'views/res_users_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_app_mass_install/static/src/js/app.js',
            'cyllo_app_mass_install/static/src/js/selected_app_details.js',
            'cyllo_app_mass_install/static/src/js/app_drawer.js',
            'cyllo_app_mass_install/static/src/xml/app_templates.xml',
            'cyllo_app_mass_install/static/src/xml/selected_app_details_templates.xml',
            'cyllo_app_mass_install/static/src/xml/app_drawer_templates.xml',
            'cyllo_app_mass_install/static/src/css/massive_app_style.css',
            'cyllo_app_mass_install/static/src/js/error_dialog.js',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True,
    'sequence': 10000,
}
