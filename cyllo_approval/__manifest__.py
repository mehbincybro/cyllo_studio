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
    'name': 'Cyllo Approval',
    'description': 'This module is used to request approvals for records',
    'summary': 'Cyllo Approvals',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base','portal'],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'wizard/approval_forward_view.xml',
        'views/approval_rule_views.xml',
        'views/approval_request_views.xml',
        'views/request_portal_template.xml',
        'views/ir_model_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_approval/static/src/systray/approval_systray.js',
            'cyllo_approval/static/src/systray/approval_systray.xml',
            'cyllo_approval/static/src/css/approval.css'
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'post_init_hook': 'create_stage_field',
}
