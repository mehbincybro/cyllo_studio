# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    use_product_warranty = fields.Boolean(
        related='team_id.use_product_warranty', string="Use Product Warranty")
    warranty_status = fields.Selection([
        ('under_warranty', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
        ('none', 'No Warranty')
    ], compute='_compute_warranty_status', string="Warranty Status Evaluation")

    @api.depends('sale_order_line_id', 'use_product_warranty')
    def _compute_warranty_status(self):
        today = fields.Date.today()
        for ticket in self:
            if not ticket.use_product_warranty or not ticket.sale_order_line_id:
                ticket.warranty_status = False
                continue
            expiration_date = ticket.sale_order_line_id.warranty_expiration_date
            if not expiration_date:
                ticket.warranty_status = 'none'
            elif expiration_date > today:
                ticket.warranty_status = 'under_warranty'
            else:
                ticket.warranty_status = 'expired'
