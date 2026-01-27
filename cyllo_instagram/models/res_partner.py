# -*- coding: utf-8 -*-
import requests
from odoo import _, fields, models


class ResPartner(models.Model):
    """
    Inherits the base res.partner model and adds Tasks information in the partner form.
    """
    _inherit = 'res.partner'

    feed_id = fields.Many2one('social.media.feed', string='Feed Related to Partner',
                              help="The feed where this contact created.")
    unique_ig_number = fields.Char(string='Feed', help="Unique identifier for the partner's feed on Facebook.")
    insta_account_id = fields.Many2one('social.insta.account', string='Instagram Account',
                                       help="Account related to partner")
    is_insta_chat = fields.Boolean(string="Instagram Chat", help="Available in Instagram chat")
    insta_chat = fields.Char(string='Chat Content', help="Last chat content.")
    insta_chat_time = fields.Datetime(string="Chat Time", help="Time of chat")

    def action_message_partner_insta(self, reply):
        """Function  to message partner through instagram"""
        account = self.insta_account_id
        self.write({
            'is_insta_chat': True,
            'insta_chat': reply,
            'insta_chat_time': fields.datetime.today()
        })
        if account and self.unique_ig_number:
            api_url = f"{account.instagram_base_url}/me/messages?access_token={account.instagram_page_access_token}"
            requests.post(api_url, json={
                "recipient": {"id": self.unique_ig_number},
                "message": {"text": reply}
            }, headers={"Content-Type": "application/json"})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Reply has been sent"),
                    'type': 'success',
                },
            }
