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
from odoo import api, fields, models


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
    posted_on_linkedin = fields.Boolean(string="Post in LinkedIn",
                                        help="Enable this to post this post in LinkedIn")

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
        """Common function for posting to social media. You can override this function in your modules."""
        self.write({
            'posted_date': fields.Datetime.now(),
            'state': 'post',
        })

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
