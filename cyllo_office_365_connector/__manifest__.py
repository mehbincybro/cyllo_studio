# -*- coding: utf-8 -*-
{
    'name': 'Cyllo office 365 Connector',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': "Cyllo-Office 365 Connector",
    'description': "This module establishes a connection between Cyllo and Office 365, enabling seamless "
                   "synchronization of contacts and to-do items.",
    'author': 'Cyllo',
    'website': "https://www.cyllo.com",
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/cyllo_office_connector_views.xml',
        'views/res_partner_views.xml',
        'views/cyllo_office_connector_menus.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
