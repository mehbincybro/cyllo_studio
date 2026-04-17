# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
    'name': 'Cyllo Helpdesk Livechat',
    'version': '1.0',
    'category': 'Services/Helpdesk',
    'summary': 'Livechat integration for Cyllo Help Desk',
    'description': "Integrates Helpdesk with Livechat to create and manage support tickets directly from live chat conversations.",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_help_desk', 'im_livechat'],
    'data': [],
'assets': {
        'web.assets_backend': [
            'cyllo_helpdesk_livechat/static/src/core/common/channel_commands.js'
        ],
},
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
