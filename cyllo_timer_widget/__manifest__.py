# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Timer Widget',
    'version': '1.2',
    'summary': """Timer widget for float field""",
    'description': """The timer widget for a float field in Odoo allows easy input and display of,
     time durations, enhancing user experience and accuracy in time management.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base_setup'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_timer_widget/static/src/css/style.css',
            'cyllo_timer_widget/static/src/js/cy_timer_widget.js',
            'cyllo_timer_widget/static/src/xml/cy_timer_widget.xml',

        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': False,
}
