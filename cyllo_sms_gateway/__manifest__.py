# -*- coding: utf-8 -*-
{
    'name': 'Multiple SMS Gateway Integration',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Module to send SMS through different SMS gateway',
    'description': "This modules helps to send SMS using different SMS gateways including "
                   "D7, Twilio, Vonage, TeleSign, MessageBird and Telnyx",
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'external_dependencies': {
        'python': ['twilio', 'clicksend_client', 'pycountry']},
    'depends': ['base', 'cyllo_base', 'sale_management', 'website'],
    'data': [
        'security/multi_sms_gateway_groups.xml',
        'security/sms_history_security.xml',
        'security/ir.model.access.csv',
        'data/sms_gateway_data.xml',
        'views/sms_history_views.xml',
        'views/portal_share_views.xml',
        'views/sms_gateway_config_views.xml',
        'wizards/send_sms_views.xml',
        'views/multi_sms_gateway_menus.xml',
        'views/website_views.xml',
        'views/login_templates.xml',
        'views/verify_otp_templates.xml',
        'views/web_login_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_sms_gateway/static/src/**/*',
        ]
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False
}
