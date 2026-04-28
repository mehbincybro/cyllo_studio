from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    appointment_ids = fields.One2many(
        'appointment.appointment', 'sale_order_id', string='Appointments'
    )
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_appointment_count'
    )

    @api.depends('appointment_ids')
    def _compute_appointment_count(self):
        for order in self:
            order.appointment_count = len(order.appointment_ids)

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'appointment.appointment',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id},
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            appointments = self.env['appointment.appointment'].sudo().search(
                [('sale_order_id', '=', order.id),
                 ('state', '=', 'pending_payment')]
            )
            for app in appointments:
                app.action_confirm()
        return res
