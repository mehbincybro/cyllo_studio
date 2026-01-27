# -*- coding: utf-8 -*-
{
    "name": "Dark Mode",
    "version": "1.0.0",
    "category": "Extra Tools",
    "summary": "Dark mode Theme",
    "description": """This module helps to set the Dark mode backend theme. And option to schedule dark mode""",
    'author': "Cyllo",
    'maintainer': "Cyllo",
    'company': "Cyllo",
    "website": "https://www.cyllo.com",
    "depends": ['cyllo_base', 'hr', 'cyllo_timepicker'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_dark_mode/static/src/lib/darkreader.js',
            'cyllo_dark_mode/static/src/js/night_mode_theme_menu.js',
            'cyllo_dark_mode/static/src/xml/systray_theme_menu_template.xml',
            'cyllo_dark_mode/static/src/scss/night_mode_theme.scss',
        ],
        'web.qunit_suite_tests': [
            'cyllo_dark_mode/static/src/tests/cy_dark_mode_menu_tests.js',
            'cyllo_dark_mode/static/src/tests/user_menu_tests.js'
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
