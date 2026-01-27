# -*- coding: utf-8 -*-
{
    'name': "Planning",
    'version': "1.0",
    'category': 'Human Resources',
    'summary': 'Planning Module for Cyllo ERP',
    'description': """The Planning Module in Cyllo ERP provides a versatile 
        solution for optimizing organizational planning and resource 
        allocation. Featuring an intuitive interface and robust Gantt view 
        functionality, users can effortlessly create, modify, and visualize 
        plans with precision. This module simplifies task and resource 
        allocation, empowering managers to boost productivity and monitor 
        timelines effectively. Leveraging the Planning module enables 
        organizations to streamline planning workflows, enhance operational 
        efficiency, and achieve better outcomes across various initiatives 
        within the Cyllo ERP.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_hr'],
    'icon': '/cyllo_planning/static/description/planning.svg',
    'data': [
        'security/ir.model.access.csv',
        'views/plan_allocation_views.xml',
        'views/allocation_type_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
