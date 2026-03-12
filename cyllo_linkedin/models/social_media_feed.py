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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SocialMediaFeed(models.Model):
    """Class to define the fields and functions for social media feeds."""
    _inherit = "social.media.feed"


    linkedin_account_id = fields.Many2one('linkedin.account',
                                          string="LinkedIn Account",
                                          help="The LinkedIn account associated with this feed.")
    linkedin_org_id = fields.Many2one(
        'linkedin.organization',
        string="LinkedIn Organization",
        help="The LinkedIn organization page this post belongs to.",
        ondelete='set null',
    )
    posted_on_linkedin = fields.Boolean(string="Posted on LinkedIn",
                                        help="If this feed is from LinkedIn")
    linkedin_post_urn = fields.Char(string="LinkedIn Post URN",
                                    help="The LinkedIn URN for this post/share")
    is_poll = fields.Boolean(string="Is Poll", default=False,
                             help="Whether this feed is a LinkedIn poll")
    poll_question = fields.Char(string="Poll Question")
    poll_options = fields.Text(string="Poll Options (JSON)",
                               help="Stored as JSON list of {text, voteCount}")
    poll_duration = fields.Char(string="Poll Duration")
    poll_total_votes = fields.Integer(string="Total Poll Votes")
    # ── Carousel / Video ────────────────────────────────────────────────────────
    carousel_images_json = fields.Text(
        string="Carousel Images (JSON)",
        help="JSON list of image URLs for multi-image (carousel) posts"
    )
    video_url = fields.Char(
        string="Video URL",
        help="Public streaming/download URL for video posts"
    )
    video_thumbnail_url = fields.Char(
        string="Video Thumbnail URL",
        help="Thumbnail image URL for video posts"
    )

    def action_social_media_comments(self):
        """Fetch comments for this feed from linkedin"""
        self.ensure_one()
        if self.posted_on_linkedin and self.linkedin_account_id:
            post_urn = self.linkedin_post_urn
            if post_urn:
                return self.linkedin_account_id.action_fetch_feed_comments(
                    post_urn)
        return []

    def action_fetch_nested_comments(self, parent_urn):
        """Fetch nested comments (replies) for a specific comment."""
        self.ensure_one()
        if self.linkedin_account_id:
            return self.linkedin_account_id.action_fetch_feed_comments(
                parent_urn)
        return []

    def unlink(self):
        """Override to delete post from LinkedIn when deleted from timeline."""
        for feed in self:
            if feed.posted_on_linkedin and feed.linkedin_account_id and feed.linkedin_post_urn:
                try:
                    res = feed.linkedin_account_id.action_delete_linkedin_post(feed.linkedin_post_urn)
                    if isinstance(res, dict) and res.get('error'):
                        raise UserError(f"Failed to delete LinkedIn post. LinkedIn API Error:\n{res['error']}")
                    if not res:
                        raise UserError("Failed to delete post from LinkedIn. Please try again or check the logs.")
                except Exception as e:
                    _logger.error(f"Failed to delete LinkedIn post {feed.linkedin_post_urn}: {e}")
                    raise UserError(f"Could not delete LinkedIn post: {e}")
        return super(SocialMediaFeed, self).unlink()