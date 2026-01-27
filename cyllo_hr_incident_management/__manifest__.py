# -*- coding: utf-8 -*-
{
    'name': "Cyllo Employee Incident Management",
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': """Efficiently manage and track employee incidents with a comprehensive incident management solution.""",
    'description': 'Cyllo Employee Incident Management provides a streamlined approach to managing employee incidents '
                   'within your organization. From incident reporting to resolution, this module offers a '
                   'user-friendly interface for HR managers and employees alike. Key features include incident '
                   'categorization, incident tracking, email notifications, and customizable incident reports.',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['cyllo_hr', 'cyllo_portal', 'cyllo_base_xlsx', 'mail'],
    'demo': [
        'data/hr_incident_category_demo.xml',
        'data/hr_incident_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_incident_security.xml',
        'data/hr_incident_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/hr_incident_views.xml',
        'views/hr_incident_category_views.xml',
        'views/incident_management_portal_view.xml',
        'views/incident_management_portal_templates.xml',
        'reports/hr_incident_report_templates.xml',
        'reports/reports.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_hr_incident_management/static/src/scss/incident_portal.scss',
            'cyllo_hr_incident_management/static/src/js/incident_request_form.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
