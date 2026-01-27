# -*- coding: utf-8 -*-
{
    'name': 'Base XLSX Report',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': """XLSX Report""",
    'description': "Generates an XLSX report based on the provided data and "
                   "returns it as a response",
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['base'],
    'assets': {
        'web.assets_backend': [
            'cyllo_base_xlsx/static/src/js/cyllo_base_xlsx.js'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
