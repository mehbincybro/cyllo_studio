# -*- coding: utf-8 -*-
{
    'name': 'Consolidation',
    'version': '1.0.0',
    'category': 'Accounting/Accounting',
    'summary': """The "cyllo_consolidation" Odoo app streamlines data management by consolidating related records or 
    information within the Odoo environment.""",
    'description': """The app merges, aggregates, or organizes data from different sources or modules, providing users 
    with a comprehensive view and enhancing decision-making and data handling efficiency.""",
    'author': 'Cyllo',
    'company': 'Cyllo',
    'maintainer': 'Cyllo',
    'website': "https://www.cyllo.com",
    'depends': ['account', 'mail', 'base', 'cyllo_base_xlsx'],
    'data': [
        'data/ir_actions_client_data.xml',
        'security/ir.model.access.csv',
        'reports/consolidated_balance_templates.xml',
        'reports/reports.xml',
        'views/consolidation_chart_views.xml',
        'views/consolidation_account_views.xml',
        'views/consolidation_group_views.xml',
        'views/consolidation_journal_views.xml',
        'views/consolidation_period_views.xml',
        'views/cyllo_consolidation_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_consolidation/static/src/js/consolidated_balance.js',
            'cyllo_consolidation/static/src/xml/consolidated_balance_templates.xml',
            'cyllo_consolidation/static/src/scss/consolidated_balance.scss'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
