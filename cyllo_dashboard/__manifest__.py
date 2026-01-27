# -*- coding: utf-8 -*-
{
    'name': 'Cyllo User Dashboard',
    'version': '1.0.0',
    "summary": "A dashboard featuring details of the current logged in user",
    "description": """
        A dashboard that displays information about the currently logged-in user. It includes various aspects such as 
        personal details, login history, upcoming activities, system performance insight and also provides access to 
        menus added to shortcuts
    """,
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': 'https://www.cyllo.com',
    'depends': ['cyllo_base'],
    'external_dependencies': {
        'python': ['geocoder']
    },
    'data': [
        'data/cron_action.xml',
        'security/cyllo_dashboard_security.xml',
        'security/ir.model.access.csv',
        'views/login_user_detail_views.xml',
        'views/change_password_dashboard.xml',
        'views/res_users_views.xml',
        'views/shortcut_menu_views.xml',
        'views/cyllo_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_dashboard/static/src/js/company_dialog.js',
            'cyllo_dashboard/static/src/js/cyllo_dashboard.js',
            'cyllo_dashboard/static/src/xml/cyllo_dashboard.xml',
            'cyllo_dashboard/static/src/xml/add_to_shortcuts.xml',
            'cyllo_dashboard/static/src/xml/remove_from_shortcuts.xml',
            'cyllo_dashboard/static/src/js/add_to_shortcuts.js',
            'cyllo_dashboard/static/src/js/remove_from_shortcuts.js',
            'cyllo_dashboard/static/src/js/form_controller.js',
            'cyllo_dashboard/static/src/css/style.css'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
