# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Portal',
    'version': "1.0.0",
    'author': 'Cyllo',
    'summary': 'This module contains the base code for cyllo customer portal',
    'description': 'This module contains the base code for cyllo customer '
                   'portal.The controllers, templates, and JavaScript files '
                   'help update the styles and functionality for the customer '
                   'portal of the Cyllo modules.',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base', 'base_setup', 'web', 'payment', 'website'],
    'data': [
        'views/portal_templates.xml',
        'views/portal_views.xml',
        'views/portal_add_address_templates.xml',
        'views/portal_address_edit_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_portal/static/src/css/cyllo_portal.css',
            'cyllo_portal/static/src/js/cyllo_portal.js',
            'cyllo_portal/static/src/js/cyllo_portal_sidebar.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
