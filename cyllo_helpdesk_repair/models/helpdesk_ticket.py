# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HelpDeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    repair_ids = fields.One2many('repair.order', 'helpdesk_ticket_id',
                                 string='Repair Orders')
    repair_count = fields.Integer(compute='_compute_repair_count')

    @api.depends('repair_ids')
    def _compute_repair_count(self):
        for ticket in self:
            ticket.repair_count = len(ticket.repair_ids)

    def action_create_repair(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['res_model'] = 'repair.order'
        action['view_mode'] = 'form'
        action['views'] = [
            (self.env.ref('repair.view_repair_order_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = {
            'default_partner_id': self.customer_id.id,
            'default_ticket_id': self.id,
            'default_helpdesk_ticket_id': self.id,
            'default_sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
            'default_sale_order_line_id': self.sale_order_line_id.id if hasattr(self, 'sale_order_line_id') and self.sale_order_line_id else False,
            'default_product_id': self.sale_order_line_id.product_id.id if hasattr(self, 'sale_order_line_id') and self.sale_order_line_id else False,
            'default_under_warranty': self.warranty_status == 'under_warranty' if hasattr(self, 'warranty_status') else False,
        }
        self.message_post(body=_("Repair Order creation initiated."))
        return action

    def action_view_repairs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "repair.action_repair_order_tree")
        action['view_mode'] = 'list,form'
        action['domain'] = [('helpdesk_ticket_id', '=', self.id)]
        return action
