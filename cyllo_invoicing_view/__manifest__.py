# -*- coding: utf-8 -*-
{
    'name': "Cyllo Invoicing View",
    'version': '1.0',
    'summary': """This module helps to add cogMenu list for invoicing's views""",
    'description': "Module to add CogMenuList in AccountMoveListController's components and "
                   "AccountMoveUploadKanbanController's components",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'account'],
    'data': {
        'views/res_config_settings_views.xml',
    },
    'assets': {
        'web.assets_backend': [
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght"
            "@400;500;600;700;800&display=swap",
            '/cyllo_invoicing_view/static/src/js/accountMoveListController.js',
        ]
    },
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': True
}
