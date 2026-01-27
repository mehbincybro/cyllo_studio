# -*- coding: utf-8 -*-
{
    'name': 'Employee Management',
    'description': 'This module is used to manage employee',
    'summary': 'Cyllo Employee Management',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'hr'],
    'data': [
        'views/cyllo_hr_menus.xml',
        'views/hr_employee_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
