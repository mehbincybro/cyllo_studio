# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket', index=True)

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered('helpdesk_ticket_id'):
            record.helpdesk_ticket_id.picking_ids = [(4, record.id)]
        return records


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, pick_type_id = super()._create_returns()
        ticket_id = self.env.context.get('default_helpdesk_ticket_id')
        if ticket_id:
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            new_picking.write({'helpdesk_ticket_id': ticket_id})
        return new_picking_id, pick_type_id
