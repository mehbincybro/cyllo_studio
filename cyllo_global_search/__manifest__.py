# -*- coding: utf-8 -*-
{
    'name': 'Global Search',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': """Enhance search functionality and enable quick creation of records in Cyllo.""",
    'description': "This Cyllo app enhances the search functionality by enabling users to search for menu items and "
                   "also quickly create records of the models where the quick create feature is enabled. "
                   "It provides a seamless experience for users to find relevant information across different "
                   "modules and efficiently create new records without navigating through multiple menus.",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['cyllo_base'],
    'data': {
        'views/ir_model_views.xml',
    },
    'assets': {
        'web.assets_backend': [
            'cyllo_global_search/static/src/scss/cyllo_global_search.scss',
            'cyllo_global_search/static/src/scss/cyllo_quick_create.scss',
            'cyllo_global_search/static/src/js/GlobalSearch.js',
            'cyllo_global_search/static/src/js/QuickCreate.js',
            'cyllo_global_search/static/src/js/action_service.js',
            'cyllo_global_search/static/src/xml/cyllo_global_search.xml',
            'cyllo_global_search/static/src/xml/quick_create.xml',
            'cyllo_global_search/static/src/xml/dialog_template.xml'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
