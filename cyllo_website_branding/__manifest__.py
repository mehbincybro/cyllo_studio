# -*- coding: utf-8 -*-
{
    'name': "Cyllo Website Branding",
    'version': '1.0',
    'summary': "Debranding default brand and replaces with Cyllo",
    'description': """
        This module helps to removes any pre-existing branding and replaces it with "Cyllo" as the new brand.
    """,
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': 'Cyllo',
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'website'],
    'assets': {
        'web.assets_backend': [
            '/cyllo_website_branding/static/src/css/style.css',
        ],
    },
    'license': "LGPL-3",
    'pre_init_hook': '_pre_init_favicon',
    'installable': True,
    'application': False,
    'auto_install': True
}
