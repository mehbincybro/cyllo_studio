# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Base Setup',
    'version': '1.0.1',
    'summary': 'The base setup module for installing cyllo_base',
    'description': 'This module helps to install cyllo_base after the database is created',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['base', 'base_setup'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
    'post_init_hook': 'install_cyllo_base'
}
