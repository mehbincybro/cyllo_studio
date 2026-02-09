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
##############################################################################

{
    'name': 'CRM Survey',
    'version': '1.0.0',
    'category': 'CRM',
    'summary': "Manage and Analyze Customer Surveys in CRM",
    'description': """This module enables creating, managing, and analyzing customer 
    survey data directly within the CRM to improve customer insights and engagement.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'crm', 'cyllo_crm', 'survey'],
    'data': [
        'data/crm_lead_survey_server_action.xml',
        'views/survey_question_views.xml',
        'views/survey_survey_views.xml',
        # 'views/crm_lead_views.xml',
    ],
    'license': "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': False,
}
