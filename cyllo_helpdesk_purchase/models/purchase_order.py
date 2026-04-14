# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)
