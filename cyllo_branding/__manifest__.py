# -*- coding: utf-8 -*-
{
    'name': "Cyllo Branding",
    'version': "1.0.0",
    'summary': 'Module for Cyllo branding',
    'description': 'This module helps to change the branding into Cyllo',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Tools',
    'depends': ['web', 'mail', 'cyllo_base'],
    'data': [
        'data/auth_signup_mail_template_demo.xml',
        'data/mail_templates_email_layouts.xml',
        'views/ir_module_views.xml',
        'views/res_config_settings_views.xml',
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_branding/static/src/js/web_client.js',
            'cyllo_branding/static/src/xml/user_menu_items.xml',
            'cyllo_branding/static/src/js/error_dialogs.js',
            'cyllo_branding/static/src/js/dialogs.js',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True,
}
