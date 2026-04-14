# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Field Service',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Field Service integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'cyllo_field_service'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
