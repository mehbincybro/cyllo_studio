# -*- coding: utf-8 -*-
{
    'name': 'Grid view',
    'version': '1.0.0',
    'author': "Cyllo",
    'summary': 'Cyllo Grid View',
    'description': """This module helps to add new grid view in the timesheet module""",
    'company': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'hr_timesheet', 'sale_management'],
    'data': ['views/cyllo_timesheet_grid_views.xml',
             'views/res_config_settings_views.xml'
             ],
    'assets': {
        'web.assets_backend': [
            'cyllo_timesheet_grid/static/src/views/GridViews/*.js',
            'cyllo_timesheet_grid/static/src/views/GridViews/*.xml',
            'cyllo_timesheet_grid/static/src/views/GridViews/grid_view.scss'
        ],
    },
    'pre_init_hook': '_pre_init_cyllo_timesheet_grid',
    'uninstall_hook': '_uninstall_hook_cyllo_timesheet_grid',
    'license': "LGPL-3",
    'installable': True,
    'application': True,
    'auto_install': True,
}
