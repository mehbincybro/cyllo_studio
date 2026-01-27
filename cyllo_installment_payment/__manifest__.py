# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Installment Payment',
    'version': '1.0.0',
    'summary': """Installment Payment for Invoices""",
    'description': "Installment payment option on invoice",
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['account', 'cyllo_advance_payment'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/installment_payment_views.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
