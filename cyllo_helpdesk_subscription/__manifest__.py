# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Subscription',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Subscription integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'sale_subscription'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
