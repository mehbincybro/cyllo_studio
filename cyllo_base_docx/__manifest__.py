# -*- coding: utf-8 -*-
{
    'name': 'Base Docx Report',
    'version': "1.0.0",
    'category': 'Accounting',
    'summary': """Docx Report""",
    'description': """Generates an Docx report based on the provided data and 
    returns it as a response""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base'],
    'assets': {
        'web.assets_backend': [
            'cyllo_base_docx/static/src/js/cyllo_base_docx.js'
        ],
    },
    'external_dependencies': {"python": ["python-docx"]},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
