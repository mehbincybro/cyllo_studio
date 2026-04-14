# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    customer_subscription_count = fields.Integer(
        compute='_compute_customer_subscription_count',
        string='Customer Subscriptions',
    )

    @api.depends('customer_id')
    def _compute_customer_subscription_count(self):
        for ticket in self:
            if not ticket.customer_id:
                ticket.customer_subscription_count = 0
                continue
            commercial_partner = ticket.customer_id.commercial_partner_id
            # Assuming subscription.order model exists in the subscription module
            ticket.customer_subscription_count = self.env[
                'subscription.order'].search_count(
                [('partner_id', 'child_of', commercial_partner.id)])

    def action_view_customer_subscriptions(self):
        self.ensure_one()
        # Assuming the action exists in cyllo_subscription or similar
        try:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "cyllo_subscription.subscription_order_action")
        except ValueError:
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Subscriptions',
                'res_model': 'subscription.order',
                'view_mode': 'tree,form',
                'target': 'current',
            }
        
        action['domain'] = [('partner_id', 'child_of',
                             self.customer_id.commercial_partner_id.id)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action
