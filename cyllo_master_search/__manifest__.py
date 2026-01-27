# -*- coding: utf-8 -*-
{
    'name': "Cyllo Master Search",
    'version': '1.0',
    'category': 'Technical',
    'summary': """Cyllo Master Search""",
    'description': """This master search tool enables you to efficiently search records within specific models. 
    It leverages the global search functionality enabled in the 'ir.model' model in Cyllo, allowing for 
    streamlined and effective record retrieval across your Cyllo instance.""",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['web'],
    'data': [
        'views/ir_model_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_master_search/static/src/css/style.css',
            'cyllo_master_search/static/src/xml/cyllo_search_bar.xml',
            'cyllo_master_search/static/src/scss/cyllo_search_bar.scss',
            'cyllo_master_search/static/src/js/cyllo_search_bar.js',
            'cyllo_master_search/static/src/js/MasterSearchDialog.js',
            'cyllo_master_search/static/src/xml/MasterSearchDialog.xml',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': True,
    'application': False,
}
