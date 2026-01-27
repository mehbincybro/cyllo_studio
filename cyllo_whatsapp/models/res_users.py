# -*- coding: utf-8 -*-
import secrets
import string
from odoo import _, api, fields, models


class ResUser(models.Model):
    """Extend the Odoo 'res.users' model to include additional fields related to
    WhatsApp integration for business accounts."""
    _inherit = 'res.users'

    phone_uid = fields.Char(string="Phone Number ID", help="Enter the whatsapp phone number ID")
    token = fields.Char(string="Access Token", help="Enter the whatsapp access token")
    webhook_callback_url = fields.Char(string="Callback URL", compute='_compute_webhook_callback_url',
                                       copy=False, help="The url foe Webhook configuration")
    app_uid = fields.Char(string="App ID", help="The Facebook application ID", tracking=True)
    account_uid = fields.Char(string="Business Account ID", tracking=True, help="The Whatsapp business account ID")
    user_ids = fields.Many2many('res.users', 'whatsapp_comfig_rel', 'cid',
                                domain=lambda self: [('share', '=', False)], string='Share Account With')

    def action_config_whatsapp_account(self):
        """ Set webhook_verify_token only when record is created, not updated after that."""
        if self.phone_uid and self.account_uid and self.app_uid and self.token:
            for user in self._origin.user_ids:
                if user.id not in self._origin.ids:
                    user.sudo().write({
                        'phone_uid': self.phone_uid,
                        'account_uid': self.account_uid,
                        'app_uid': self.app_uid,
                        'token': self.token,
                    })
            self.user_ids = False
        else:
            self.user_ids = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Account details such as App ID, Business Account Id, Phone Number Id, "
                                 "Access Token have to be filled to share this account."),
                    'type': 'warning',
                },
            }

    def _generate_token(self, length=7):
        """Generate a random token."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

    def _compute_webhook_callback_url(self):
        """Compute the callback URL for the current record.
        This method generates a callback URL by combining the base URL of the
        Odoo instance with the endpoint '/whatsapp/message'. The resulting URL
        is assigned to the 'webhook_callback_url' field
        of the current record.
        :return: None"""
        for record in self:
            record.webhook_callback_url = record.get_base_url() + '/whatsapp/message'

    def get_user_data(self, uid):
        """Retrieves user data based on user ID.
            Args:
                uid (int): The ID of the user.
            Returns:
                dict: A dictionary containing user data including token, phone UID, app UID, and account UID."""
        user = self.sudo().browse(uid)
        return {
            'token': user.token,
            'phone_uid': user.phone_uid,
            'app_uid': user.app_uid,
            'account_uid': user.account_uid,
        }

    def action_update_data(self, account_uid, app_uid, phone_uid, token):
        """Updates user data with the provided values.
            Args:
                account_uid (int): The account UID to update.
                app_uid (int): The app UID to update.
                phone_uid (int): The phone UID to update.
                token (str): The token to update.
            Returns:
                None"""
        self.sudo().write({
            'account_uid': account_uid,
            'app_uid': app_uid,
            'phone_uid': phone_uid,
            'token': token,
        })

    @api.model
    def get_whatsapp_user_view(self):
        """Retrieves the view of the WhatsApp user.
        This method returns the view of the WhatsApp user by accessing the view with the reference
        'cyllo_whatsapp.view_res_users_form'.
        Returns:
           dict: A dictionary representing the view of the WhatsApp user."""
        return self.env.ref("cyllo_whatsapp.view_res_users_form").sudo().read()
