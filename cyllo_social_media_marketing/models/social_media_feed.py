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
from odoo import fields, models


class SocialMediaFeed(models.Model):
    """Class to define the fields and functions for social media feeds."""
    _name = "social.media.feed"
    _description = "Social Media Feeds"

    description = fields.Text(string="Content",
                              help="Description for the feed created")
    author_name = fields.Char(string='Name of Author',
                              help="The responsible person of this post")
    posted_image_url = fields.Char(string="Image Url", help="Posted image url")
    profile_image_url = fields.Char(string="Profile Picture Url",
                                    help="Profile picture of the author url")
    profile_image_bs64 = fields.Image(
        string="Image",
        help="The base image of the user",
    )
    author_link_url = fields.Char(string="Author Url", help="Author url")
    author_link = fields.Html(string="Link of Author",
                              help="The responsible account link")
    posted_date = fields.Date(string="Date of Posting",
                              help="Date at which this post was published")
    posted_image = fields.Html(string="Image", help="Posted image")
    profile_image = fields.Html(string="Profile Picture",
                                help="Profile picture of the author")
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media post.")
    likes_count = fields.Integer(string="Likes",
                                 help="Number of likes on the post")
    comments_count = fields.Integer(string="Comments",
                                    help="Number of comments on the post")
    post_id = fields.Many2one('social.media.post', string="Related Post",
                              help="Post related to the feed created.")

    def action_compute_likes_count_all(self):
        """Compute the number of likes on the post for all feed."""
        return True

    def action_compute_likes_count(self):
        """Compute the number of likes on the post for Instagram."""
        for feed in self:
            if hasattr(feed, 'views_count'):
                return {
                    'likes_count': feed.likes_count,
                    'comments_count': feed.comments_count,
                    'views_count': feed.views_count,
                }
            else:
                return {
                    'likes_count': feed.likes_count,
                    'comments_count': feed.comments_count,
                }

    def action_social_media_comments(self):
        """Placeholder function for handling social media comments."""
        return

    def action_social_media_likes(self):
        """
        Placeholder function for handling social media likes.
        """
        return

    def get_dashboard_data(self):
        dashboard_data = []
        model_names = self.env['ir.model'].search_read([], ['model'])
        existing_models = set(model['model'] for model in model_names)
        if 'social.fb.account' in existing_models:
            facebook_accounts = self.env['social.fb.account'].search(
                [('state', '=', 'connected')])
            for account in facebook_accounts:
                feeds = self.env['social.media.feed'].search(
                    [('fb_account_id', '=', account.id)])
                total_posts = len(feeds)
                total_likes = sum(feed.likes_count for feed in feeds)
                total_comments = sum(feed.comments_count for feed in feeds)

                dashboard_data.append({
                    'id': account.id,
                    'account_name': account.facebook_page_name,
                    'platform': 'social.fb.account',
                    'total_posts': total_posts,
                    'total_likes': total_likes,
                    'total_comments': total_comments,
                })

        if 'social.insta.account' in existing_models:
            insta_accounts = self.env['social.insta.account'].search(
                [('state', '=', 'connected')])
            for account in insta_accounts:
                posts = self.env['social.media.feed'].search(
                    [('ig_account_id', '=', account.id)])
                total_posts = len(posts)
                total_likes = sum(
                    post.likes_count for post in posts) if posts else 0
                total_comments = sum(
                    post.comments_count for post in posts) if posts else 0

                dashboard_data.append({
                    'id': account.id,
                    'account_name': account.facebook_insta_page_name,
                    'platform': 'social.insta.account',
                    'total_posts': total_posts,
                    'total_likes': total_likes,
                    'total_comments': total_comments,
                })

        if 'youtube.account' in existing_models:
            youtube_accounts = self.env['youtube.account'].search(
                [('state', '=', 'sync')])
            for account in youtube_accounts:
                videos = self.env['social.media.feed'].search([(
                    'post_id.youtube_channel_id.youtube_account_id',
                    '=',
                    account.id)])
                total_videos = len(videos)
                total_likes = sum(
                    video.likes_count for video in videos) if videos else 0
                total_comments = sum(
                    video.comments_count for video in videos) if videos else 0
                dashboard_data.append({
                    'id': account.id,
                    'account_name': account.name,
                    'platform': 'youtube.account',
                    'total_posts': total_videos,
                    'total_likes': total_likes,
                    'total_comments': total_comments,
                })
        return {
            'dashboard_data': dashboard_data,
            'posts': self.search([]).read()}

    def action_create_connect(self, data,platform):
        account = self.env[platform].sudo().create(data)
        if platform =="social.fb.account":
            account.action_connect()
        if platform =="social.insta.account":
            account.action_connect_instagram()
        if platform =="youtube.account":
            account.action_get_authorization_url()
            return account.id
        return False

    def get_model(self,model):
        if model == 'social.fb.account':
            name = 'cyllo_facebook'
        elif model == 'social.insta.account':
            name = 'cyllo_instagram'
        else:
            name = 'cyllo_youtube'
        module=self.env['ir.module.module'].sudo().search([('name','=',name),('state', '=', 'installed')])
        if module:
            return True
        else:
            return False
