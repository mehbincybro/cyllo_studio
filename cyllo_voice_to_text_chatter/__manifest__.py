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
    'name': 'Voice To Text Chatter',
    'version': '1.0',
    'category': 'Productivity',
    'summary': """Add voice option in the chatter""",
    'description': """The module helps you to Chat with voice.""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base','web','cyllo_web','mail'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_voice_to_text_chatter/static/src/xml/composer.xml',
            'cyllo_voice_to_text_chatter/static/src/js/composer.js',
            'cyllo_voice_to_text_chatter/static/src/js/voice_to_text.js',
            'cyllo_voice_to_text_chatter/static/src/xml/voice_to_text.xml',
        ],
    },
    'license': "LGPL-3",
    'installable': True,
    'application': True,
    'auto_install': False,
}
