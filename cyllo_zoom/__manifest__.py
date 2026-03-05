# -*- coding: utf-8 -*-
{
    'name': 'Zoom',
    'category': 'Extra tool',
    'version': '1.0',
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'summary': 'Meeting with cyllo',
    'description': """
        Cyllo zoom is a application to link with zoom in activity type.
        Zoom credentials are configured globally in Settings → General Settings
        → Zoom Integration and apply to all users.
    """,
    'depends': ['base_setup', 'cyllo_base', 'sale', 'crm', 'mail'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_config_settings_view.xml',
        'views/calendar_event_views.xml',
        'views/calender_event_quick_form_view.xml',
    ],

    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
