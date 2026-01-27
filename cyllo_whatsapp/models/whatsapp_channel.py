# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WhatsappChannel(models.Model):
    """Model representing a Whatsapp Channel for Messages."""
    _description = 'Whatsapp Channel for Messages'
    _name = 'whatsapp.channel'

    name = fields.Char('Name', required=True, help='Channel Name')
    active = fields.Boolean(default=True, help="Set active to false to hide the channel without removing it.")
    partner_id = fields.Many2one('res.partner', string='Partners', help='Partner to chat with',
                                 ondelete='restrict')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 help='Select the company')
    wa_message_ids = fields.One2many('whatsapp.message', 'channel_id',
                                     help='The Messages in this channel')
    sender_id = fields.Many2one('res.partner', help='Partner responsible for this chat',
                                default=lambda self: self.env.user.partner_id.id)
    user_id = fields.Many2one('res.users', help='User responsible for this chat',
                              default=lambda self: self.env.user.id)
    message_count = fields.Integer(compute='_compute_message_count', store=True)
    last_message = fields.Char('Last Message', help='Last message on this channel')
    last_messenger = fields.Char('Name of Messenger', help='Last messenger on this channel')

    @api.depends('wa_message_ids.is_read')
    def _compute_message_count(self):
        """Compute the count of unread messages in the channel."""
        for rec in self:
            rec.message_count = self.wa_message_ids.search_count([('is_read', '=', False), ('flag', '=', False)])
