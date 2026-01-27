# -*- coding: utf-8 -*-
{
    'name': "Cyllo Employee Service/Custody Management",
    'version': "1.0",
    'category': 'Human Resources',
    'summary': """A Module to handle employee service and custody""",
    'description': 'module is designed to streamline the management of employee services and custody within an '
                   'organization. It provides a comprehensive solution for tracking various aspects related to '
                   'employee services',
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_hr', 'cyllo_portal', 'hr_maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/hr_service_views.xml',
        'views/hr_service_category_views.xml',
        'views/maintenance_request_views.xml',
        'views/service_management_portal_templates.xml',
        'views/service_portal_views.xml',
        'reports/hr_service_report_template.xml',
        'reports/reports.xml',
        'wizards/late_return_reason.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_hr_service_management/static/src/scss/service_portal.scss',
            'cyllo_hr_service_management/static/src/js/ServicePortal.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
