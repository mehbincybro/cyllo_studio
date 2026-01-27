# -*- coding: utf-8 -*-
import requests
from dateutil.relativedelta import relativedelta

from odoo import _, fields, models


class SocialInstaAccount(models.Model):
    """Class to define the fields and functions for Facebook Account."""
    _name = "social.insta.account"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Social Media Instagram Account"
    _rec_name = "facebook_insta_page_name"

    instagram_access_token = fields.Char(string='Access Token', required=True,
                                         help="""Instagram Access Token provided by the Facebook API.""")
    instagram_page_access_token = fields.Char(string='Facebook Page Access Token', required=True,
                                              help="""Facebook Page Access Token provided by the Facebook API.""")
    facebook_insta_page_number = fields.Char(string='Page ID', help="""Facebook Page ID provided by the Facebook API""")
    facebook_insta_page_name = fields.Char(string='Page Name', required=True,
                                           help="""Facebook Page Name provided by the Facebook API""")
    instagram_base_url = fields.Char(string='Instagram Base Url Latest', required=True,
                                     default="https://graph.facebook.com/v18.0",
                                     help="""Base url of Instagram integration update the latest version.""")
    Instagram_connection_authenticated = fields.Boolean(string="Instagram Connection Completed",
                                                        help="Boolean field which signifies the connection.")
    meta_app_number = fields.Char(string='Meta App Id', required=True, help="Meta account app id")
    meta_app_secret = fields.Char(string='Meta App Secrets', required=True, help="Meta account app secrets")
    renewal_date = fields.Date(string='Renewal Date of Access Token', help="Date for the renewal, the access token must"
                                                                           " be renewed within 5 days after this day")
    instagram_account_number = fields.Char(string='Instagram Id', help="Connected Instagram account id.")
    instagram_business_account_number = fields.Char(string='Instagram Business Id',
                                                    help="Connected Instagram account id.")
    state = fields.Selection([('not connected', 'Not Connected'), ('connected', 'Connected')],
                             required=True, default='not connected', tracking=True)

    def action_connect_instagram(self):
        """Function to connect Instagram account and authenticate the connection."""
        try:
            url = f'{self.instagram_base_url}/me/accounts?access_token={self.instagram_access_token}'
            response = requests.get(url).json()
            if response.get('error'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {'message': _(response.get('error')['message']), 'type': 'warning'},
                }
            if response.get('data') and self.facebook_insta_page_name:
                name_list = []
                for data in response['data']:
                    name_list.append(data['name'])
                    if data['name'] == self.facebook_insta_page_name:
                        self.write({'facebook_insta_page_number': data['id'],
                                    'state': 'connected',
                                    'Instagram_connection_authenticated': True})
                        self.message_post(body="Page ID fetched Successfully")
                if self.facebook_insta_page_name not in name_list:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {'message': _("Page not found with given name"), 'type': 'warning'},
                    }
                business_url = (f"{self.instagram_base_url}/{self.facebook_insta_page_number}?fields=id,name,"
                                f"instagram_business_account&access_token={self.instagram_page_access_token}")
                business_url_response = requests.get(business_url).json()
                self.instagram_business_account_number = business_url_response.get('instagram_business_account')['id']
                insta_url = (f"{self.instagram_base_url}/{self.facebook_insta_page_number}/instagram_accounts?"
                             f"access_token={self.instagram_page_access_token}&fields=id,username,profile_pic")
                datas = requests.get(insta_url).json()
                self.instagram_account_number = datas.get('data')[0].get('id')
                if not self.renewal_date or self.renewal_date < fields.date.today():
                    self.refresh_access_token()
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Page not found.Fill the proper data and try again"),
                        'type': 'warning',
                    },
                }
        except Exception:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Please verify that the provided credentials are accurate and ensure that your device "
                                 "is connected to the internet"),
                    'type': 'warning',
                },
            }

    def action_disconnect(self):
        """Function to disconnect the Instagram account."""
        self.write({
            'state': 'not connected',
            'Instagram_connection_authenticated': False,
            'renewal_date': False,
        })

    def refresh_access_token(self):
        """Function to refresh the Instagram access token."""
        base_url = f"{self.instagram_base_url}/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.meta_app_number,
            'client_secret': self.meta_app_secret,
            'fb_exchange_token': self.instagram_access_token,
        }
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        result = response.json()
        long_lived_token = result.get('access_token')
        self.instagram_access_token = long_lived_token
        user_id_url = f"{self.instagram_base_url}/me?access_token={long_lived_token}"
        response = requests.get(user_id_url)
        user_id = response.json().get('id')
        long_live_page_token_url = f"{self.instagram_base_url}/{user_id}/accounts?access_token={long_lived_token}"
        response = requests.get(long_live_page_token_url)
        for page in response.json()['data']:
            if page.get('id') == self.facebook_insta_page_number:
                self.instagram_page_access_token = page.get('access_token')
        self.renewal_date = fields.Date.today() + relativedelta(days=50)
