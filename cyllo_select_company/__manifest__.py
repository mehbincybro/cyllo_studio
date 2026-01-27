# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Select Company',
    'version': '1.0.0',
    'summary': """A single menu option to select all or swtich to main company at once instead of individually selecting them""",
    'description': """This module simplifies company selection in Cyllo by adding a menu option to toggle selecting
     all companies at once. It offers a convenient alternative to individually selecting or deselecting companies.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'web'],
    'assets': {
        'web.assets_backend': [
            'cyllo_select_company/static/src/webclient/switchCompanyMenu.xml',
            'cyllo_select_company/static/src/webclient/switchCompanyMenu.js',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
