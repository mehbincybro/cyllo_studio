# -*- coding: utf-8 -*-
{
    "name": "Import Bank Statement",
    "version": "1.0.0",
    "category": "Account",
    "summary": """Import Bank Statement""",
    "description": """This module facilitates the 
    seamless import of financial statements in various formats such as CSV, 
    XLSX, XLS, OFX, and QIF into the system.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    "website": "https://www.cyllo.com",
    "depends": ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/import_bank_statement_views.xml',
        'views/cyllo_bank_statement_import_menu.xml',
    ],
    'license': "LGPL-3",
    'external_dependencies': {'python': ['pandas', 'qifparse', 'openpyxl', 'xlrd']},
    'installable': True,
    'auto_install': False,
    'application': False,
}
