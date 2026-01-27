# -*- coding: utf-8 -*-
from odoo import fields, models


class MailMessage(models.Model):
    """ Extended Mail Message class to add custom actions."""
    _inherit = 'mail.message'

    is_possible_lead = fields.Boolean(string="Possible to Make Lead", help="Thi message can be converted to lead")

    def action_reply_message(self, reply):
        """ Method for replying to a message."""
        return True

    def action_create_lead(self):
        """ Action to create lead on the basis of message."""
        return False

    def action_reply_message_chatter(self, sender_id, reply, res_id):
        """ Method for replying to a message from chatter."""
        return True
