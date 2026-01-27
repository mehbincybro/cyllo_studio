# -*- coding: utf-8 -*-
{
    'name':  'Cyllo DHL Connector',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Integrate DHL shipping services with Odoo',
    'description': """The DHL Connector module for Odoo allows you to integrate 
     DHL shipping services into your Odoo instance.This module simplifies the
     shipping process, making it easier for businesses to use DHL's
     global shipping services while maintaining control and visibility through 
     the Odoo platform.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'sale_management', 'delivery', 'stock', 'website', 'portal', 'website_sale'],
    'data': [
        'data/product_product_data.xml',
        'views/delivery_carrier_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
