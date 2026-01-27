# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    """ Class to add a reference field in invoice to connect Support service
    and invoice """
    _inherit = "account.move"

    ticket_reference = fields.Char(help="Reference for support service ticket")
    ticket_id = fields.Many2one('support.service.ticket', string="Support Service Ticket")
