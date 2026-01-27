# -*- coding: utf-8 -*-
{
    'name': "POS Debranding",
    'version': "1.0.0",
    'summary': 'Debranding the default brand from POS',
    'description': 'Install the module to remove all the predefined brands of '
                   'the parent company from POS',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Tools',
    'depends': ['cyllo_base', 'point_of_sale'],
    'data': [
        'views/pos_assets_index.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cyllo_pos_branding/static/src/**/*',
            'cyllo_pos_branding/static/src/xml/overrides/components/receipt_screen/order_receipt/order_receipt.xml'
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True,
}
