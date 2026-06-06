# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class FrontdeskVisitor(models.Model):
    _inherit = 'frontdesk.visitor'

    expected_arrival = fields.Datetime(string='Expected Arrival', tracking=True)
    appointment_id = fields.Many2one('appointment.appointment', string='Linked Appointment', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer/Partner', tracking=True)

    def action_check_in(self):
        res = super().action_check_in()
        for visitor in self:
            if visitor.appointment_id:
                visitor.appointment_id.action_start()
        return res

    def action_check_out(self):
        res = super().action_check_out()
        for visitor in self:
            if visitor.appointment_id:
                visitor.appointment_id.action_done()
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for visitor in self:
            if visitor.appointment_id and visitor.appointment_id.state != 'cancelled':
                visitor.appointment_id.write({
                    'state': 'cancelled',
                    'cancellation_reason': _('Visitor registration was cancelled from the front desk.'),
                    'cancelled_by': 'staff',
                })
        return res

    def action_book_now(self):
        self.ensure_one()
        if self.appointment_id:
            raise UserError(_("This visitor already has a linked appointment."))

        # 1. Ensure partner_id is set
        if not self.partner_id:
            partner = False
            # Try matching by email
            if self.email:
                partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)
            # Try matching by phone/mobile
            if not partner and self.phone:
                partner = self.env['res.partner'].search(['|', ('phone', '=', self.phone), ('mobile', '=', self.phone)], limit=1)
            # Try matching by name
            if not partner and self.name:
                partner = self.env['res.partner'].search([('name', '=', self.name)], limit=1)
            
            # Create if not found
            if not partner:
                partner_vals = {
                    'name': self.name,
                    'email': self.email,
                    'phone': self.phone,
                }
                if self.company:
                    company_partner = self.env['res.partner'].search([
                        ('name', '=', self.company),
                        ('is_company', '=', True)
                    ], limit=1)
                    if not company_partner:
                        company_partner = self.env['res.partner'].create({
                            'name': self.company,
                            'is_company': True
                        })
                    partner_vals['parent_id'] = company_partner.id
                partner = self.env['res.partner'].create(partner_vals)
            
            self.partner_id = partner.id

        # 2. Return action to open pre-filled appointment form view
        return {
            'name': _('Book Appointment'),
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.appointment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_staff_id': self.host_id.id if self.host_id else False,
                'default_station_id': self.station_id.id,
                'default_appointment_type_id': self.station_id.appointment_type_id.id if self.station_id.appointment_type_id else False,
                'default_visitor_id': self.id,
            }
        }
