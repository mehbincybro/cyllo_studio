from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


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
            if not order.appointment_ids:
                continue
            if order.invoice_status == 'to invoice':
                try:
                    invoices = order._create_invoices()
                    invoices.action_post()
                    _logger.info(
                        'Auto-created invoice(s) %s for appointment '
                        'order %s.', invoices.mapped('name'), order.name
                    )
                except Exception as e:
                    _logger.warning(
                        'Failed to auto-create invoice for appointment '
                        'order %s: %s', order.name, str(e)
                    )
            pending = order.appointment_ids.filtered(
                lambda a: a.state == 'pending_payment'
            )
            for appt in pending:
                try:
                    appt.action_confirm()
                except Exception as e:
                    _logger.warning(
                        'Failed to confirm appointment %s: %s',
                        appt.name, str(e)
                    )
        return res
