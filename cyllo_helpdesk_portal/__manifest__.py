# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Portal',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Portal integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'portal'],
    'data': [
        'views/helpdesk_portal_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
