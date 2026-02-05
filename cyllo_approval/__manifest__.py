# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Approval',
    'description': 'This module is used to request approvals for records',
    'summary': 'Cyllo Approvals',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base','mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/approval_rule_views.xml',
        'views/approval_request_views.xml',
        'views/ir_buttons_views.xml',
        'wizard/approval_request_wizard_views.xml',
        'wizard/approval_transfer_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [

        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': 'post_init_load_buttons',
}
