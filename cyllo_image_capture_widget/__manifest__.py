# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Image Capture Widget',
    'version': '1.0.0',
    'category': 'Extra tools',
    'summary': """The Image Capture Widget module in Odoo enables users to capture and upload images directly""",
    'description': """The Image Capture Widget module integrates a convenient image capture feature into Odoo,
     enabling users to capture and upload images directly from their devices within the Odoo interface.""",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base'],
    'assets': {
        'web.assets_backend': [
            '/cyllo_image_capture_widget/static/src/js/image_capture.js',
            '/cyllo_image_capture_widget/static/src/xml/image_capture_templates.xml',
        ],
    },
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
