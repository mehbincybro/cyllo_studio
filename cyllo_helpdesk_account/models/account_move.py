# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)
