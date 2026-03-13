# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Cyllo Help Desk',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': """Help Desk Management""",
    'description': "Manage helpdesk tickets, SLAs, teams, reporting, dashboard, ratings, and daily targets.",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'mail', 'im_livechat', 'sale', 'hr_timesheet', 'rating', 'crm', 'repair', 'stock', 'sale_loyalty', 'project', 'portal', 'website'],
    'data': [
        'security/cyllo_help_desk_security_group.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_stage_data.xml',
        'data/website_form_data.xml',
        'data/cyllo_help_desk_mail_template.xml',
        'data/cyllo_help_desk_mail_template_issue_solved.xml',
        'data/onboarding_data.xml',
        'reports/helpdesk_ticket_report.xml',
        'reports/helpdesk_ticket_report_templates.xml',
        'reports/helpdesk_ticket_pdf_report.xml',
        'reports/helpdesk_ticket_pdf_report_templates.xml',
        'wizard/helpdesk_report_views.xml',
        'wizard/helpdesk_ticket_merge_wizard_views.xml',
        'data/helpdesk_ticket_cron.xml',
        'views/helpdesk_portal_templates.xml',
        'views/helpdesk_overview_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_my_ticket_views.xml',
        'views/helpdesk_analysis_views.xml',
        'views/daily_target_views.xml',
        'views/helpdesk_category_views.xml',
        'views/helpdesk_tag_views.xml',
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_sla_views.xml',
        'views/sla_status_views.xml',
        'views/helpdesk_skill_views.xml',
        'views/helpdesk_canned_response_views.xml',
        'views/customer_rating_view.xml',
        'views/cyllo_help_desk_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_help_desk/static/src/core/common/channel_commands.js',
            'cyllo_help_desk/static/src/views/helpdesk_overview.xml',
            'cyllo_help_desk/static/src/js/helpdesk_overview.js',
            'cyllo_help_desk/static/src/views/helpdesk_team_kanbanview.xml',
            'cyllo_help_desk/static/src/js/helpdesk_team_kanbanview.js',
        ],
        'im_livechat.assets_embed_core': [
            'cyllo_help_desk/static/src/core/common/channel_commands.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
