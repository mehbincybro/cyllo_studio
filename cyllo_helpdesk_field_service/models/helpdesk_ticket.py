# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    field_service_request_ids = fields.One2many('field.service.request',
                                                'helpdesk_ticket_id',
                                                string='Field Service Requests')
    field_service_request_count = fields.Integer(
        compute='_compute_field_service_request_count')

    @api.depends('field_service_request_ids')
    def _compute_field_service_request_count(self):
        for ticket in self:
            ticket.field_service_request_count = len(
                ticket.field_service_request_ids)

    def action_create_field_service_request(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_field_service.action_view_all_requests")
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref(
            'cyllo_field_service.view_field_service_request_form').id, 'form')]
        action['target'] = 'current'
        priority_map = {
            '0': 'b',
            '1': 'a',
            '2': 'c',
            '3': 'd',
        }
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_description': self.description,
            'default_helpdesk_ticket_id': self.id,
            'default_priority': priority_map.get(self.priority, 'a'),
            'default_sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
        }
        self.message_post(body=_("Field Service Request creation initiated."))
        return action

    def action_view_field_service_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_field_service.action_view_all_requests")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action
