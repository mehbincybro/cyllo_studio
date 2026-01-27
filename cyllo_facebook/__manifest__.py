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
    'name': 'Facebook',
    'version': "1.0",
    'category': 'Marketing',
    'summary': """This module is used to manage facebook account""",
    'description': """This module is used to manage facebook account and also
     create post in the configured account""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'mail', 'cyllo_social_media_marketing'],
    'icon': '/cyllo_facebook/static/description/facebook.svg',
    'data': [
        'data/mail_message_subtype_data.xml',
        'views/ir_attachment_views.xml',
        'views/social_media_post_views.xml',
        'views/res_partner_views.xml',
        'views/social_media_feed_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_facebook/static/src/js/facebook_comments.js',
            'cyllo_facebook/static/src/xml/facebook_comment_template.xml',
            'cyllo_facebook/static/src/xml/chat_window_template.xml',
            'cyllo_facebook/static/src/xml/chatter.xml',
            'cyllo_facebook/static/src/systray/fb_systray.js',
            'cyllo_facebook/static/src/systray/fb_systray.xml',
            'cyllo_facebook/static/src/js/chatter.js',
            'cyllo_facebook/static/src/xml/suggestedReciepient.xml',
            'cyllo_facebook/static/src/js/feed_dashboard_fb.js',
            'cyllo_facebook/static/src/xml/feed_dashboard_fb.xml',
        ],
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
