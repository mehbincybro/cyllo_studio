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
from odoo import api, fields, models, _
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class SocialMediaPost(models.Model):
    """Class to define the fields and functions for social media posts."""
    _name = "social.media.post"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Post"

    name = fields.Char(string="Reference", required=True, help="Reference for the social media post.")
    active = fields.Boolean(string='Archive', default=True, help="Check this to activate the social media post.")
    description = fields.Text(string="Content", required=True, help="Content of the social media post.")
    company_id = fields.Many2one(string="Related Company", comodel_name='res.company',
                                 default=lambda self: self.env.company.id, required=True, index=True,
                                 help="The company associated with the social media post.")
    posted_date = fields.Datetime(string="Date of Posting", readonly=True,
                                  help="Date and time when the post was published.")
    user_id = fields.Many2one('res.users', string="Created User", required=True,
                              default=lambda self: self.env.user, index=True, ondelete='cascade',
                              help="User who created the social media post.")
    ir_attachment_ids = fields.Many2many('ir.attachment', string="Add Media",
                                         help="Media files attached to the post.")
    state = fields.Selection([('draft', 'Draft'), ('queue', 'On-Queue'), ('post', 'Posted'),
                              ('delete', 'Deleted')], default='draft', copy=False,
                             help="State of the social media post.")
    feed_count = fields.Char(compute="_compute_feed_count", string="Feed",
                             help="Count of social media feeds associated with the post.")
    mode = fields.Selection([('url', 'Url'), ('attachment', 'Attachment'),
                             ('content_only', 'Content Only (Only applicable in facebook)')],
                            default='url', copy=False, help="Mode of the social media post.")
    post_url = fields.Char(string="URL of Post", help="Url attachment of the post.")
    posted_on_linkedin = fields.Boolean(string="Post in LinkedIn", help="Enable this to post this post in LinkedIn")
    linkedin_account_ids = fields.Many2many('linkedin.account', string="LinkedIn Accounts",
                                         help="LinkedIn connected accounts")
    linkedin_organization_ids = fields.Many2many('linkedin.organization', string="LinkedIn Pages",
                                              help="Specific LinkedIn organization pages to post to.")

    @api.onchange('mode')
    def _onchange_mode(self):
        """Function to select account on the basis of mode"""
        if self.mode == 'content_only' and hasattr(self, 'post_on_instagram'):
            self.write({'post_on_instagram': False})
        if self.mode == 'content_only' and hasattr(self, 'posted_on_linkedin'):
            self.write({'posted_on_linkedin': False})

    def _compute_feed_count(self):
        """Compute the count of social media feeds associated with the post."""
        for post in self:
            post.feed_count = self.env['social.media.feed'].search_count([('post_id', '=', post.id)])

    def action_post(self):
        """Common function for posting to social media."""

        for post in self:
            linkedin_success = True
            if post.posted_on_linkedin:
                for org in post.linkedin_organization_ids:
                    account = org.account_id
                    if not account.linkedin_access_token or not org.org_urn:
                        _logger.warning(f"LinkedIn organization {org.name} missing token or URN.")
                        continue

                    url = 'https://api.linkedin.com/v2/ugcPosts'
                    headers = {
                        'Authorization': f'Bearer {account.linkedin_access_token}',
                        'X-Restli-Protocol-Version': '2.0.0',
                        'Content-Type': 'application/json',
                    }

                    owner_urn = org.org_urn
                    _logger.info(f"Posting to LinkedIn with author URN: {owner_urn}")

                    payload = {
                        "author": owner_urn,
                        "lifecycleState": "PUBLISHED",
                        "specificContent": {
                            "com.linkedin.ugc.ShareContent": {
                                "shareCommentary": {
                                    "text": post.description
                                },
                                "shareMediaCategory": "NONE"
                            }
                        },
                        "visibility": {
                            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                        }
                    }

                    if post.mode == 'url' and post.post_url:
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"
                        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                            "status": "READY",
                            "originalUrl": post.post_url,
                            "title": { "text": post.name }
                        }]

                    try:
                        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
                        if response.status_code == 201:
                            result = response.json()
                            post_id = result.get('id')
                            self.env['social.media.feed'].create({
                                'description': post.description,
                                'posted_date': fields.Datetime.now(),
                                'author_name': org.name,
                                'linkedin_account_id': account.id,
                                'linkedin_org_id': org.id,
                                'posted_on_linkedin': True,
                                'post_id': post.id,
                                'author_link_url': f"https://www.linkedin.com/feed/update/{post_id}" if post_id else False
                            })
                            self.message_post(body=_("Successfully posted to LinkedIn (%s)") % org.name)
                        else:
                            linkedin_success = False
                            error_msg = response.text
                            _logger.error(f"LinkedIn API error ({response.status_code}): {error_msg}")
                            self.message_post(body=_(
                                "Failed to post to LinkedIn (%s).\n"
                                "URN used: %s\n"
                                "Error: %s\n\n"
                                "TIP: If this is an organization page, ensure you have the 'w_organization_social' permission."
                            ) % (org.name, owner_urn, error_msg))
                    except Exception as e:
                        linkedin_success = False
                        _logger.exception("LinkedIn post exception")
                        self.message_post(body=_(f"Exception while posting to LinkedIn: {str(e)}"))

            if linkedin_success:
                post.write({
                    'posted_date': fields.Datetime.now(),
                    'state': 'post',
                })
            else:
                pass

    def action_open_feed(self):
        """Action to open associated social media feeds."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Feed',
            'view_mode': 'kanban',
            'res_model': 'social.media.feed',
            'domain': [('post_id', '=', self.id)],
            'context': "{'create': False}"
        }
