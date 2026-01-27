# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Budget Project',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': """Project Add/Create from Budget""",
    'description': "We can add/create project from budget in Budget Management",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'maintainer': 'Cyllo',
    'depends': ['project', 'cyllo_budget_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/budget_project_wizard.xml',
        'views/budget_budget_view_inherit.xml',
        'views/project_project_view_inherit.xml',

    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
