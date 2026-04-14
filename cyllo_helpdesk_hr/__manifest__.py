# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk HR',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'HR Skills integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'hr', 'hr_skills'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
