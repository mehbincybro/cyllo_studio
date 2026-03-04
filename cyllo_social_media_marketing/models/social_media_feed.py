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
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class SocialMediaFeed(models.Model):
    """Class to define the fields and functions for social media feeds."""
    _name = "social.media.feed"
    _description = "Social Media Feeds"
    _order = "posted_date desc, id desc"

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
    posted_date = fields.Datetime(string="Date of Posting",
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
    linkedin_account_id = fields.Many2one('linkedin.account', string="LinkedIn Account",
                                       help="The LinkedIn account associated with this feed.")
    linkedin_org_id = fields.Many2one(
        'linkedin.organization',
        string="LinkedIn Organization",
        help="The LinkedIn organization page this post belongs to.",
        ondelete='set null',
    )
    posted_on_linkedin = fields.Boolean(string="Posted on LinkedIn", help="If this feed is from LinkedIn")
    linkedin_post_urn = fields.Char(string="LinkedIn Post URN", help="The LinkedIn URN for this post/share")
    # ── Poll fields ─────────────────────────────────────────────────────────────
    is_poll = fields.Boolean(string="Is Poll", default=False, help="Whether this feed is a LinkedIn poll")
    poll_question = fields.Char(string="Poll Question")
    poll_options = fields.Text(string="Poll Options (JSON)", help="Stored as JSON list of {text, voteCount}")
    poll_duration = fields.Char(string="Poll Duration")
    poll_total_votes = fields.Integer(string="Total Poll Votes")

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
        """Fetch comments for this feed from the respective social platform."""
        self.ensure_one()
        if self.posted_on_linkedin and self.linkedin_account_id:
            post_urn = self.linkedin_post_urn
            if post_urn:
                return self.linkedin_account_id.action_fetch_feed_comments(post_urn)
        return []

    def action_fetch_nested_comments(self, parent_urn):
        """Fetch nested comments (replies) for a specific comment."""
        self.ensure_one()
        if self.linkedin_account_id:
            return self.linkedin_account_id.action_fetch_feed_comments(parent_urn)
        return []

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

        if 'linkedin.account' in existing_models:
            linkedin_accounts = self.env['linkedin.account'].search(
                [('state', '=', 'connected')])
            for account in linkedin_accounts:
                feeds = self.env['social.media.feed'].search(
                    [('linkedin_account_id', '=', account.id)])
                total_posts = len(feeds)
                total_likes = sum(feed.likes_count for feed in feeds)
                total_comments = sum(feed.comments_count for feed in feeds)

                dashboard_data.append({
                    'id': account.id,
                    'account_name': account.name,
                    'platform': 'linkedin.account',
                    'total_posts': total_posts,
                    'total_likes': total_likes,
                    'total_comments': total_comments,
                })
        return {
            'dashboard_data': dashboard_data,
            'posts': self.search([], order='posted_date desc, id desc').read()}

    def action_create_connect(self, data,platform):
        account = self.env[platform].sudo().create(data)
        if platform =="social.fb.account":
            account.action_connect()
        if platform =="social.insta.account":
            account.action_connect_instagram()
        if platform =="youtube.account":
            account.action_get_authorization_url()
        if platform =="linkedin.account":
            account.action_connect_linkedin()
            return account.id
        return False

    def get_model(self,model):
        if model == 'social.fb.account':
            name = 'cyllo_facebook'
        elif model == 'social.insta.account':
            name = 'cyllo_instagram'
        elif model == 'youtube.account':
            name = 'cyllo_youtube'
        else:
            name = 'cyllo_hr_linkedin_recruitment'
        module=self.env['ir.module.module'].sudo().search([('name','=',name),('state', '=', 'installed')])
        if module:
            return True
        else:
            return False

    def unlink(self):
        """Override to delete post from LinkedIn when deleted from Odoo timeline."""
        for feed in self:
            if feed.posted_on_linkedin and feed.linkedin_account_id and feed.linkedin_post_urn:
                try:
                    feed.linkedin_account_id.action_delete_linkedin_post(feed.linkedin_post_urn)
                except Exception as e:
                    _logger.error(f"Failed to delete LinkedIn post {feed.linkedin_post_urn}: {e}")
        return super(SocialMediaFeed, self).unlink()
