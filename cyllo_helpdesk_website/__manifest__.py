# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Website',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Website integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'website'],
    'data': [
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_helpdesk_website/static/src/js/website_helpdesk_editor.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
