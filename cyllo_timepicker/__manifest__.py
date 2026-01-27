# -*- coding: utf-8 -*-
{
    'name': 'Time Picker',
    'version': '1.0.0',
    'category': 'Extra Tools',
    'summary': 'Time Picker Widget',
    'description': """This module helps to add time picker widget for a character field""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base'],
    "assets": {
        'web.assets_backend': [
            'cyllo_timepicker/static/src/lib/wickedpicker.js',
            'cyllo_timepicker/static/src/js/time_widget.js',
            'cyllo_timepicker/static/src/css/wickedpicker.css',
            'cyllo_timepicker/static/src/xml/timepicker.xml',
            'cyllo_timepicker/static/src/scss/timepicker.scss'
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': True,
    'application': False,
}
