# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Loyalty',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Coupon/Loyalty integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'sale_loyalty'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
