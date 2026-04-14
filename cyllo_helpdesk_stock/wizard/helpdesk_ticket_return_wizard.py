# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketReturnWizard(models.TransientModel):
    _name = 'helpdesk.ticket.return.wizard'
    _description = 'Helpdesk Ticket Return Wizard'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', readonly=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)

    def action_confirm(self):
        self.ensure_one()
        action = self.env.ref('stock.act_stock_return_picking').read()[0]
        action['context'] = {
            'active_id': self.picking_id.id,
            'active_ids': [self.picking_id.id],
            'active_model': 'stock.picking',
            'default_helpdesk_ticket_id': self.ticket_id.id,
        }
        return action
