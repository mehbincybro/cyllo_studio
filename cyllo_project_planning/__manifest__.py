# -*- coding: utf-8 -*-
{
    'name': "Cyllo Project Planning",
    'version': "1.0",
    'category': 'Human Resources',
    'summary': """Project Planning Module for Cyllo ERP""",
    'description': """Cyllo Project Planning is a module that allows users to plan their tasks within projects.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_planning', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/plan_allocation_views.xml',
        'views/project_task_views.xml',
        'wizards/project_plan_allocation_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
