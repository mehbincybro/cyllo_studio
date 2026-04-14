# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Warranty',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Product Warranty integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'cyllo_product_warranty','cyllo_helpdesk_sale'],
    'data': [
        'views/helpdesk_ticket_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
