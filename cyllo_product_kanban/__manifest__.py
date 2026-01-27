# -*- coding: utf-8 -*-
{
    'name': "Cyllo Product Kanban",
    'description': 'Cyllo product kanban',
    'summary': 'The module shows the product kanban',
    'version': '1.0',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'data': ['views/product_template_views.xml'],
    'depends': ['cyllo_base', 'product'],
    'assets': {
        'web.assets_backend': [
            '/cyllo_product_kanban/static/src/css/style.css',
            '/cyllo_product_kanban/static/src/js/kanbanController.js'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': True
}
