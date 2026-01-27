# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Budget Crm',
    'version': '1.0.0',
    'category': 'Accounting',
    'summary': """Sales person target in Budget""",
    'description': "We can add sales person from budget and can see the achievement in CRM",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'maintainer': 'Cyllo',
    'depends': ['crm', 'cyllo_budget_management'],
    'data': [
        'views/budget_budget_view.xml',
        'views/crm_team_member_view.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
