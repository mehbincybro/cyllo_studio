# -*- coding: utf-8 -*-
{
    'name': 'One2many Search and Delete Widget',
    'version': "1.0",
    'category': 'Extra Tools',
    'summary': 'Widgets for search and delete one2many records',
    'description': 'The module helps multiple deletion and search the records'
                   ' in one2many numerically and alphabetically',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'cyllo_o2m_search_delete_widget/static/src/css/InputBox.css',
            'cyllo_o2m_search_delete_widget/static/src/xml/X2ManyField.xml',
            'cyllo_o2m_search_delete_widget/static/src/js/X2ManyField.js'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
