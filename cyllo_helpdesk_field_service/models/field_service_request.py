# -*- coding: utf-8 -*-
from odoo import fields, models


class FieldServiceRequest(models.Model):
    _inherit = 'field.service.request'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)
