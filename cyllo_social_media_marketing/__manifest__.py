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
    'name': 'Social Media Marketing',
    'version': "1.0",
    'category': 'Marketing',
    'summary': "Base module for Social Media Marketing",
    'description': "Base module for Social Media Marketing and for all"
                   " depending module",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'mail', 'crm'],
    'icon': '/cyllo_social_media_marketing/static/description/social-marketing.svg',
    'data': [
        'security/social_media_marketing_security.xml',
        'security/ir.model.access.csv',
        'views/social_media_post_views.xml',
        'views/social_media_feed_views.xml',
        'views/social_fb_account_views.xml',
        'views/social_insta_account_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_social_media_marketing/static/src/js/channel_selector.js',
            'cyllo_social_media_marketing/static/src/js/messaging_menu.js',
            'cyllo_social_media_marketing/static/src/js/chat_window_service.js',
            'cyllo_social_media_marketing/static/src/js/chatter.js',
            'cyllo_social_media_marketing/static/src/js/feed_dashboard.js',
            'cyllo_social_media_marketing/static/src/js/social_media_dashboard.js',
            'cyllo_social_media_marketing/static/src/xml/social_media_dashboard.xml',
            'cyllo_social_media_marketing/static/src/scss/social_media_dashboard.scss',
            'cyllo_social_media_marketing/static/src/xml/feed_dashboard_template.xml',
            'cyllo_social_media_marketing/static/src/js/chatter.js',
            'cyllo_social_media_marketing/static/src/js/chatter_container.js',
            'cyllo_social_media_marketing/static/src/js/chatter_action.js',
            'cyllo_social_media_marketing/static/src/scss/kanban.scss',
        ],
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
