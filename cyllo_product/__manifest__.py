# -*- coding: utf-8 -*-
{
    'name': 'Products',
    'version': "1.0.0",
    'Category': 'Extra Tools',
    'summary': 'A dashboard to show product related details',
    'description': 'The "Product Dashboard" app is a comprehensive tool for '
                   'managing and analyzing product-related data, providing '
                   'valuable insights and statistics to help businesses make '
                   'informed decisions about their products.',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'depends': ['product'],
    'website': "https://www.cyllo.com",
    'data': [
        'security/ir.model.access.csv',
        'security/cyllo_product_security.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_menus.xml',
        'wizards/product_reject_views.xml',
    ],
    'images': [''],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
