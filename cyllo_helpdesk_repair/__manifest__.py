# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Repair',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Repair integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'repair'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
