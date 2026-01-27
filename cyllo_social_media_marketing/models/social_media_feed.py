# -*- coding: utf-8 -*-
from odoo import fields, models


class SocialMediaFeed(models.Model):
    """Class to define the fields and functions for social media feeds."""
    _name = "social.media.feed"
    _description = "Social Media Feeds"

    description = fields.Text(string="Content", help="Description for the feed created")
    author_name = fields.Char(string='Name of Author', help="The responsible person of this post")
    posted_image_url = fields.Char(string="Image Url", help="Posted image url")
    profile_image_url = fields.Char(string="Profile Picture Url", help="Profile picture of the author url")
    author_link_url = fields.Char(string="Author Url", help="Author url")
    author_link = fields.Html(string="Link of Author", help="The responsible account link")
    posted_date = fields.Date(string="Date of Posting", help="Date at which this post was published")
    posted_image = fields.Html(string="Image", help="Posted image")
    profile_image = fields.Html(string="Profile Picture", help="Profile picture of the author")
    company_id = fields.Many2one(string="Related Company", comodel_name='res.company',
                                 default=lambda self: self.env.company.id, required=True, index=True,
                                 help="The company associated with the social media post.")
    likes_count = fields.Integer(string="Likes", help="Number of likes on the post")
    comments_count = fields.Integer(string="Comments", help="Number of comments on the post")
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
