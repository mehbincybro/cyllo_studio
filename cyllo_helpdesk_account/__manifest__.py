# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Account',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Accounting integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'account'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
