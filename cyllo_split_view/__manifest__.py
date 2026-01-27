# -*- coding: utf-8 -*-
{
    'name': "Cyllo Split View",
    'version': '1.0.0',
    'summary': 'Split the view of list',
    'description': 'This module enhances the functionality of the tree view by '
                   'splitting it for every model. It then integrates the other '
                   'half as a form view for each selected record',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['web', 'cyllo_base'],
    'assets': {
        'web.assets_backend': [
            "cyllo_split_view/static/src/css/chatter.css",
            "cyllo_split_view/static/src/js/ListController.js",
            "cyllo_split_view/static/src/js/ListRenderer.js",
            "cyllo_split_view/static/src/xml/list_view.xml",
            'cyllo_split_view/static/src/js/split_view.js',
            'cyllo_split_view/static/src/xml/split_view.xml',
            'cyllo_split_view/static/src/js/FormController.js',
            'cyllo_split_view/static/src/xml/form_view.xml',
            'cyllo_split_view/static/src/js/ButtonBox.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
