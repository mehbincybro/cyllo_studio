# -*- coding: utf-8 -*-
from odoo import fields, models


class RepairOrder(models.Model):
    """ Class to add a ticket field in invoice to connect Support service
        and repair order"""
    _inherit = 'repair.order'

    ticket_id = fields.Many2one('support.service.ticket', string="Support Service Ticket")
