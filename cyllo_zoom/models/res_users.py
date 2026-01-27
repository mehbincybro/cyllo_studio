# -*- coding: utf-8 -*-
import requests

from odoo import _, fields, models, api
from odoo.exceptions import UserError
import base64
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

TIMEOUT = 20


class ResUsers(models.Model):
    """Extending res users  to add additional fields in the res user to connect the zoom account """
    _inherit = "res.users"

    zoom_client = fields.Char(string="Client Id",
                              help='Zoom Developer Console Client ID')
    zoom_client_secret = fields.Char(string="Client Secret",
                                     help='Zoom Developer Console Client Secret')
    zoom_redirect_uri = fields.Char(string="Authorized redirect URIs",
                                    default="http://localhost:8017"
                                            "/zoom/callback",
                                    help='Zoom Authorized redirect URIs')
    zoom_code = fields.Char(help='Authorization Code '
                                 'for respective user', readonly=True)
    zoom_token = fields.Char(string='Access Token',
                             copy=False,
                             help='Access token for '
                                  'respective user', readonly=True)
    zoom_token_expiry = fields.Datetime(string='Token expiry',
                                        help='Access token expiration',
                                        readonly=True)
    zoom_refresh_token = fields.Char(string='Refresh Token',
                                     copy=False,
                                     help='Refresh token for '
                                          'respective user')
    zoom_status = fields.Selection(
        selection=[('not_connected', 'Not Connected'),
                   ('connected', 'Connected')])

    zoom_recordings = fields.Char(string="Zoom Recording Location",
                                  default="/home/cybrosys/Documents/Zoom",
                                  help='Zoom Recordings')
    def action_connect_zoom(self):
        """Redirect the user to Zoom's OAuth authorization page"""
        self.ensure_one()
        if not (self.zoom_client or self.zoom_client_secret):
            raise UserError(_("Please configure Client id"))
        base_url = 'https://zoom.us/oauth/authorize'
        zoom_url = (
            f"{base_url}"
            f"?response_type=code"
            f"&client_id={self.zoom_client}"
            f"&redirect_uri={self.zoom_redirect_uri}"
            f"&state={self.id}"
        )
        return {'type': 'ir.actions.act_url', 'url': zoom_url,
                'target': 'current'}

    def action_zoom_meet_refresh_token(self):
        """Generate or refresh Zoom access token for a user"""
        for user in self:
            if not user.zoom_client:
                raise UserError(_('Client ID is not yet configured.'))
            if not user.zoom_client_secret:
                raise UserError(_('Client Secret is not yet configured.'))
            if not user.zoom_refresh_token:
                raise UserError(_('Refresh Token is not yet configured.'))

            b64_code = f"{user.zoom_client}:{user.zoom_client_secret}".encode(
                'utf-8')
            b64 = base64.b64encode(b64_code).decode('utf-8')

            data = {
                'refresh_token': user.zoom_refresh_token,
                'grant_type': 'refresh_token',
            }

            try:
                response = requests.post(
                    'https://zoom.us/oauth/token',
                    data=data,
                    headers={
                        'Authorization': f'Basic {b64}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout=TIMEOUT
                )
                resp_json = response.json()
                _logger.info("Zoom refresh response for %s: %s", user.name,
                             resp_json)

                if resp_json.get('access_token'):
                    user.write({
                        'zoom_token': resp_json.get('access_token'),
                        'zoom_token_expiry': fields.Datetime.now() + timedelta(
                            seconds=resp_json.get('expires_in', 3599)
                        ),
                        'zoom_refresh_token': resp_json.get('refresh_token',
                                                            user.zoom_refresh_token)
                    })
                    # Refresh the record to have the latest values in memory
                    _logger.info("Updated Zoom token expiry for %s: %s",
                                 user.name, user.zoom_token_expiry)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _(
                                "Toke is Generated Successfully"),
                            'type': 'success',
                            'sticky': True,
                            'next': {'type': 'ir.actions.act_window_close'},
                        },
                    }
                else:
                    error_reason = resp_json.get('reason', resp_json)
                    raise UserError(
                        _('Zoom token refresh failed: %s') % error_reason)

            except requests.exceptions.RequestException as e:
                _logger.exception("HTTP request to Zoom failed for user %s: %s",
                                  user.name, e)

                raise UserError(
                    _('Zoom token refresh failed due to network error.'))

    @api.model
    def _cron_check_and_refresh_zoom_tokens(self):
        """Automatically refresh Zoom tokens for users whose tokens are expiring soon"""

        expiring_users = self.sudo().search([
            ('zoom_status', '=', 'connected'),
        ])
        _logger.info("Found %d users with expiring Zoom tokens",
                     len(expiring_users))

        for user in expiring_users:
            try:
                _logger.info("Refreshing Zoom token for user: %s", user.name)
                user.sudo().action_zoom_meet_refresh_token()
                _logger.info("New Zoom token expiry for %s: %s", user.name,
                             user.zoom_token_expiry)
            except UserError as e:
                _logger.warning("Skipping user %s due to token issue: %s",
                                user.name, e)
            except Exception as e:
                _logger.exception(
                    "Unexpected error while refreshing token for user %s: %s",
                    user.name, e)
