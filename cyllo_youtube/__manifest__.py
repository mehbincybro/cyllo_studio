# -*- coding: utf-8 -*-
{
    'name': 'Cyllo Youtube',
    'category': 'Extra tool',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'summary': "Integrate YouTube functionality into the Cyllo Social Media Marketing module.",
    'description': """This module extends the functionality of the Cyllo Social Media Marketing module by integrating YouTube features. It allows users to manage YouTube accounts, channels, and posts """,
    'depends': ['base','mail','cyllo_social_media_marketing'],
    'data': [
        'security/ir.model.access.csv',
        'views/youtube_account_views.xml',
        'views/youtube_channel_views.xml',
        'views/social_media_feed_views.xml',
        'views/social_media_post_views.xml',
        'wizards/upload_video_wizard_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_youtube/static/src/xml/youtube_comment_template.xml',
            'cyllo_youtube/static/src/xml/feed_dashboard_youtube.xml',
            'cyllo_youtube/static/src/js/youtube_comments.js',
            'cyllo_youtube/static/src/js/feed_dashboard_youtube.js',
            'cyllo_youtube/static/src/xml/file_to_path.xml',
            'cyllo_youtube/static/src/js/file_to_path.js',
        ],
    },
    'images': [
        'static/src/img/default_image.png',
    ],
    'license': "LGPL-3",
    'installable': True,
    'application': False,
    'auto_install': False,
}
