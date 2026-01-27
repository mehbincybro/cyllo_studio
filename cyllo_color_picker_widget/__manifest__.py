# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Color Picker Widget',
    'version': '1.0.0',
    'category': 'Extra tools',
    'summary': """Color Picker widget for Cyllo""",
    'description': "The Color Picker widget for Cyllo improves user experience by providing an attractive "
                   "and efficient way to choose colors within fields.",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base'],
    'assets': {
        'web.assets_backend': [
            '/cyllo_color_picker_widget/static/src/xml/color_picker.xml',
            '/cyllo_color_picker_widget/static/src/css/color_picker.css',
            '/cyllo_color_picker_widget/static/src/js/color_picker.js',
        ],
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
