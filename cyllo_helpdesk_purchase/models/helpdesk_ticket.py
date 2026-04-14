# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    customer_purchase_order_count = fields.Integer(
        compute='_compute_customer_purchase_order_count',
        string='Customer Purchase Orders',
    )

    @api.depends('customer_id')
    def _compute_customer_purchase_order_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_purchase_order_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            ticket.customer_purchase_order_count = self.env[
                'purchase.order'].search_count(
                [('partner_id', 'child_of', commercial_partner.id)])

    def action_view_customer_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase.purchase_form_action")
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        action['view_mode'] = 'tree'
        action['views'] = [
            (self.env.ref('purchase.purchase_order_view_tree').id, 'tree')]
        return action
