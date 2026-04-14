# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Sale',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Sale Order integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'sale','cyllo_product_warranty'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
