# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Helpdesk Stock',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Return/Replacement integration for Cyllo Help Desk',
    'depends': ['cyllo_help_desk', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/helpdesk_ticket_return_wizard_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_team_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
