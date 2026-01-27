# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Instagram',
    'version': '1.0.0',
    'category': 'Marketing',
    'summary': """This module is used to manage instagram account""",
    'description': """This module is used to manage instagram account and also
     create post in the configured account""",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'mail', 'cyllo_social_media_marketing'],
    'icon': '/cyllo_instagram/static/description/instagram.svg',
    'data': [
        'data/mail_message_subtype.xml',
        'views/ir_attachment_views.xml',
        'views/social_media_post_views.xml',
        'views/social_media_feed_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_instagram/static/src/js/instagram_comments.js',
            'cyllo_instagram/static/src/xml/instagram_comment_template.xml',
            'cyllo_instagram/static/src/systray/ig_systray.xml',
            'cyllo_instagram/static/src/systray/ig_systray.js',
            'cyllo_instagram/static/src/xml/chatter.xml',
            'cyllo_instagram/static/src/js/chatter.js',
            'cyllo_instagram/static/src/xml/suggestedReciepient.xml',
            'cyllo_instagram/static/src/js/feed_dashboard_insta.js',
            'cyllo_instagram/static/src/xml/feed_dashboard_insta.xml',
        ],
    },
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
