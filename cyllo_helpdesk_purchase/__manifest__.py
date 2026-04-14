# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Purchase',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Purchase integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'purchase'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
