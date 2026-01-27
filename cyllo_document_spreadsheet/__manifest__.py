# -*- coding: utf-8 -*-
{
    "name": "Document Spreadsheet",
    "version": "1.0",
    "category": "Extra Tools",
    "summary": """Manage excel files for document""",
    "description": "User can upload and create excel file and spreadsheet",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    "depends": ["cyllo_spreadsheet", "cyllo_documents"],
    "data": [
        "security/ir.model.access.csv",
        "data/document_workspace_data.xml",
        "wizards/create_excel_views.xml"
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_document_spreadsheet/static/src/js/kanbanController.js',
            'cyllo_document_spreadsheet/static/src/xml/kanbanController.xml',
            "cyllo_document_spreadsheet/static/src/js/spreadsheet_share_action.js"
        ],
        "spreadsheet.o_spreadsheet": [
            "cyllo_document_spreadsheet/static/src/spreadsheet/bundle/spreadsheet_share_action_loader.js",
            "cyllo_document_spreadsheet/static/src/spreadsheet/bundle/spreadsheet_renderer.js",
            "cyllo_document_spreadsheet/static/src/spreadsheet/bundle/spreadsheet_action.js",
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'uninstall_hook': 'uninstall_hook',
}
