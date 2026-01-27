# -*- coding: utf-8 -*-
import requests
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models


class SocialFbAccount(models.Model):
    """
    Class to define the fields and functions for Facebook Account.
    """
    _name = "social.fb.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Facebook Account"
    _rec_name = "facebook_page_name"

    facebook_access_token = fields.Char(string='Page Access Token', required=True,
                                        help="""Facebook Access Token provided by the Facebook API.""")
    facebook_user_access_token = fields.Char(string='User Access Token', required=True,
                                             help="""Facebook User Access Token provided by the Facebook API.""")
    facebook_page_number = fields.Char(string='Page ID', help="""Facebook Page ID provided by the Facebook API""")
    facebook_page_name = fields.Char(string='Page Name', required=True,
                                     help="""Facebook Page Name provided by the Facebook API""")
    facebook_base_url = fields.Char(string='Facebook Base Url Latest', required=True,
                                    default="https://graph.facebook.com/v18.0",
                                    help="""Base url of facebook integration update the latest version.""")
    facebook_connection_authenticated = fields.Boolean(string="Facebook Connection Completed", readonly=True,
                                                       help="Boolean signifies the connection of account")
    meta_app_number = fields.Char(string='Meta App Id', required=True, help="Meta account app id")
    meta_app_secret = fields.Char(string='Meta App Secrets', required=True, help="Meta account app secrets")
    expiry_date = fields.Date(string='Expiry Date of Access tokens',
                              help='Date at which access token must be refreshed')
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)

    def action_connect(self):
        """ Function to connect Facebook account and authenticate the connection. """
        try:
            url = f'{self.facebook_base_url}/me/accounts?access_token={self.facebook_user_access_token}'
            response = requests.get(url).json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(response.get('error')['message']), 'type': 'warning'},
                }
            if response.get('data') and self.facebook_page_name:
                name_list = []
                for data in response['data']:
                    name_list.append(data['name'])
                    if data['name'] == self.facebook_page_name:
                        self.write({
                            'facebook_page_number': data['id'],
                            'facebook_connection_authenticated': True
                        })
                        self.message_post(body="Page ID fetched Successfully.", )
                        self.write({
                            'state': 'connected',
                            'facebook_connection_authenticated': True,
                        })
                if self.facebook_page_name not in name_list:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'message': _("Page not found with given name"), 'type': 'warning'},
                    }
                if not self.expiry_date or self.expiry_date < fields.date.today():
                    self.refresh_access_token()
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _("Page not found.Fill the proper data and try again"), 'type': 'warning'},
                }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that "
                                 "your device is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_disconnect(self):
        """ Function to disconnect the Facebook account. """
        self.write({
            'state': 'not connected',
            'facebook_connection_authenticated': False,
        })

    def refresh_access_token(self):
        """ Function to refresh the Facebook access token. """
        base_url = f"{self.facebook_base_url}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.meta_app_number,
            'client_secret': self.meta_app_secret,
            'fb_exchange_token': self.facebook_user_access_token,
        }
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        result = response.json()
        long_lived_token = result.get('access_token')
        self.facebook_user_access_token = long_lived_token
        user_id_url = f"{self.facebook_base_url}/me?access_token={long_lived_token}"
        response = requests.get(user_id_url)
        user_id = response.json().get('id')
        long_live_page_token_url = f"{self.facebook_base_url}/{user_id}/accounts?access_token={long_lived_token}"
        response = requests.get(long_live_page_token_url)
        for page in response.json()['data']:
            if page.get('id') == self.facebook_page_number:
                self.facebook_access_token = page.get('access_token')
        self.expiry_date = fields.Date.today() + relativedelta(days=50)
