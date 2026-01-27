# -*- coding: utf-8 -*-
{
    "name": "Marketing Automation",
    "version": "1.0.0",
    "category": "Marketing",
    "summary": """Marketing Automation streamlines and improves marketing 
    efforts through technology""",
    "description": """Marketing Automation is the use of technology to automate 
    and optimize marketing processes, enhancing efficiency and personalizing 
    customer experiences.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    "website": "https://www.cyllo.com",
    "depends": ['base', 'mail', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/marketing_activity_action.xml',
        'views/marketing_campaign_views.xml',
        'views/ir_model_views.xml',
        'views/marketing_filter_views.xml',
        'views/cyllo_marketing_automation_menus.xml',
        'views/marketing_activity_views.xml',
        'views/marketing_participant_views.xml',
        'views/marketing_activity_line_views.xml',
        'wizards/mail_composer_message_views.xml',
        'views/mailing_trace_views.xml',
        'views/mailing_mailing_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_marketing_automation/static/src/js/marketing_activity.js',
            'cyllo_marketing_automation/static/src/js/marketing_cards.js',
            'cyllo_marketing_automation/static/src/js/marketing_child.js',
            'cyllo_marketing_automation/static/src/xml/marketing_activity_childs.xml',
            'cyllo_marketing_automation/static/src/xml/marketing_activity_card.xml',
            'cyllo_marketing_automation/static/src/js/marketing_tabs.js',
            'cyllo_marketing_automation/static/src/js/useSaveContext.js',
            'cyllo_marketing_automation/static/src/xml/marketing_activity_tabs.xml',
            'cyllo_marketing_automation/static/src/xml/marketing_activity_template.xml',
            'cyllo_marketing_automation/static/src/xml/activity_recursive_componet.xml',
            'cyllo_marketing_automation/static/src/js/activity_recursive_component.js',
            'cyllo_marketing_automation/static/src/js/activity_test_widget.js',
            'cyllo_marketing_automation/static/src/xml/activity_test_widget_view.xml',
            'cyllo_marketing_automation/static/src/scss/marketing.scss'
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}
