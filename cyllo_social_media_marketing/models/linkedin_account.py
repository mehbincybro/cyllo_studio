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

import requests
import logging
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from werkzeug.urls import url_encode, url_join
import urllib.parse
import re

_logger = logging.getLogger(__name__)


class LinkedInAccount(models.Model):
    """
    Model representing a Social Media LinkedIn Account.
    """
    _name = "linkedin.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media LinkedIn Account"

    name = fields.Char(string="Name", required=True)
    username = fields.Char(string="Username", help="Optional. Enter to autofill LinkedIn login page.")
    linkedin_access_token = fields.Char(string='Access Token', help='Access token for your linkedin app')
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)
    linkedin_profile_image_url = fields.Char(string='Logo URL', help='LinkedIn Organization Logo URL')
    company_id = fields.Many2one(string="Related Company",
                                 comodel_name='res.company',
                                 default=lambda self: self.env.company.id,
                                 required=True, index=True,
                                 help="The company associated with the social media account.")
    last_sync_orgs = fields.Datetime(string='Last Orgs Sync', help='Last time organizations were synced from LinkedIn')
    is_default = fields.Boolean(string="Is Default", compute="_compute_is_default", store=False)


    @api.model_create_single
    def create(self, vals):
        """Override to handle manual access token connection."""
        if vals.get('linkedin_access_token'):
            vals['state'] = 'connected'
        record = super(LinkedInAccount, self).create(vals)
        if record.linkedin_access_token:
            try:
                record.action_sync_organizations()
            except Exception as e:
                _logger.error(f"Failed to sync organizations for manual account {record.name}: {e}")
        
        return record


    def _compute_is_default(self):
        default_id = self.env['ir.config_parameter'].sudo().get_param(
            'social_linkedin_account.default_account_id'
        )
        for rec in self:
            rec.is_default = str(rec.id) == str(default_id)

    def action_connect_linkedin(self):
        """Connect LinkedIn account via OAuth only."""
        self.ensure_one()
        linkedin_auth_provider = self.env.ref(
            'cyllo_hr_linkedin_recruitment.provider_linkedin'
        )
        if not linkedin_auth_provider.client_id or not linkedin_auth_provider.client_secret:
            raise ValidationError(_(
                'LinkedIn Access Credentials are empty!\n'
                'Please fill them in the Auth Provider form.'
            ))
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url')
        redirect_uri = url_join(base_url, '/linkedin/redirect')
        params = {
            'response_type': 'code',
            'client_id': linkedin_auth_provider.client_id,
            'redirect_uri': redirect_uri,
            'state': f'smm_{self.id}',
            'scope': (
                'openid profile email '
                'w_member_social '
                # 'r_organization_social '
                # 'rw_organization_admin '
                # 'w_organization_social'
            ),
        }
        if self.username:
            params['login_hint'] = self.username
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://www.linkedin.com/oauth/v2/authorization?%s' % url_encode(
                params),
            'target': 'self',
        }

    def action_disconnect(self):
        """ Function to disconnect the LinkedIn account. """
        self.write({
            'state': 'not connected',
            'linkedin_access_token': False,
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'social_linkedin_account.default_account_id', None
        )
