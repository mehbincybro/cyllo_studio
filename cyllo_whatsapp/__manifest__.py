# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Whatsapp',
    'category': 'Extra tool',
    'version': '1.0',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'summary': 'Enhance communication with WhatsApp integration for Cyllo ERP.',
    'description': """
        Cyllo Whatsapp is a module for Cyllo ERP, designed to enhance communication capabilities 
        by seamlessly integrating with WhatsApp. This module empowers users to send WhatsApp messages 
        directly from Cyllo ERP, share links via WhatsApp, and integrate WhatsApp functionality 
        into various workflows within the Cyllo ERP platform. With Cyllo Whatsapp, organizations 
        can streamline their communication processes and leverage the popularity and convenience 
        of WhatsApp for business purposes, all within the Cyllo ERP environment.
    """,
    'depends': ['cyllo_base', 'sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'security/cyllo_whatsapp_security.xml',
        'data/whatsapp_template_preview_data.xml',
        'views/res_users_views.xml',
        'wizards/whatsapp_template_message.xml',
        'wizards/whatsapp_template_preview_views.xml',
        'wizards/portal_share_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_channel_views.xml',
        'views/whatsapp_menu.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_whatsapp/static/src/systray/*',
            'cyllo_whatsapp/static/src/chatter/*',
            'cyllo_whatsapp/static/src/css/*',
            'cyllo_whatsapp/static/src/scss/*',
            'cyllo_whatsapp/static/src/xml/*',
            'cyllo_whatsapp/static/src/js/*'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'post_init_hook': 'get_country_phone_codes',
    'application': False,
    'auto_install': False,
}
