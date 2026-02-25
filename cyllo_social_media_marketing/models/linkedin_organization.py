# -*- coding: utf-8 -*-
import logging
import requests
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class LinkedInOrganization(models.Model):
    """Represents a LinkedIn Company/Organization page linked to a LinkedIn account."""
    _name = 'linkedin.organization'
    _description = 'LinkedIn Organization'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    org_urn = fields.Char(
        string='URN',
        help='LinkedIn URN, e.g. urn:li:organization:123 or urn:li:person:456',
        required=True,
        index=True,
    )
    type = fields.Selection([
        ('person', 'Person'),
        ('organization', 'Organization')
    ], string='Type', default='organization', required=True)
    logo_url = fields.Char(string='Logo URL', help='LinkedIn organization logo URL')
    account_id = fields.Many2one(
        'linkedin.account',
        string='LinkedIn Account',
        required=True,
        ondelete='cascade',
    )
    state = fields.Selection(
        [('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        string='State',
    )
    feed_ids = fields.One2many(
        'social.media.feed',
        'linkedin_org_id',
        string='Feeds',
    )
    feed_count = fields.Integer(
        string='Feed Count',
        compute='_compute_feed_count',
    )

    def _compute_feed_count(self):
        for org in self:
            org.feed_count = len(org.feed_ids)

    def action_fetch_feeds(self):
        """Fetch LinkedIn posts for this organization page only."""
        self.ensure_one()
        account = self.account_id
        if not account.linkedin_access_token:
            return
        legacy_headers = {'Authorization': f'Bearer {account.linkedin_access_token}'}
        count = account._fetch_feeds_for_urn(
            self.org_urn,
            self.name,
            self.logo_url,
            legacy_headers,
            org_id=self.id,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'{count} new posts synced for {self.name}.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def get_org_data(self):
        """Return a dict suitable for the frontend."""
        return {
            'id': self.id,
            'name': self.name,
            'org_urn': self.org_urn,
            'logo_url': self.logo_url or False,
        }
