# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    station_id = fields.Many2one(
        'frontdesk.frontdesk', 
        string='Default Front Desk Station',
        help='Default front desk station assigned to appointments of this type.'
    )


class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    station_id = fields.Many2one(
        'frontdesk.frontdesk', 
        string='Front Desk Station',
        help='Front desk station assigned to this appointment.'
    )
    visitor_id = fields.Many2one(
        'frontdesk.visitor',
        string='Source Visitor',
        help='Visitor for whom this appointment was booked.'
    )

    @api.onchange('appointment_type_id')
    def _onchange_appointment_type_id_station(self):
        if self.appointment_type_id and self.appointment_type_id.station_id:
            self.station_id = self.appointment_type_id.station_id

    def write(self, vals):
        confirming_appointments = self.env['appointment.appointment']
        if vals.get('state') == 'confirmed':
            confirming_appointments = self.filtered(lambda a: a.state != 'confirmed')

        started_appointments = self.env['appointment.appointment']
        if vals.get('state') == 'in_progress':
            started_appointments = self.filtered(lambda a: a.state != 'in_progress')

        done_appointments = self.env['appointment.appointment']
        if vals.get('state') == 'done':
            done_appointments = self.filtered(lambda a: a.state != 'done')

        cancelled_appointments = self.env['appointment.appointment']
        if vals.get('state') == 'cancelled':
            cancelled_appointments = self.filtered(lambda a: a.state != 'cancelled')

        res = super().write(vals)

        if confirming_appointments:
            confirming_appointments._create_frontdesk_visitors()

        if started_appointments:
            visitors_to_check_in = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', started_appointments.ids),
                ('state', '=', 'planned')
            ])
            if visitors_to_check_in:
                visitors_to_check_in.action_check_in()

        if done_appointments:
            visitors_to_check_out = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', done_appointments.ids),
                ('state', '=', 'checked_in')
            ])
            if visitors_to_check_out:
                visitors_to_check_out.action_check_out()

        if cancelled_appointments:
            visitors_to_cancel = self.env['frontdesk.visitor'].search([
                ('appointment_id', 'in', cancelled_appointments.ids),
                ('state', 'not in', ('cancelled', 'checked_out'))
            ])
            if visitors_to_cancel:
                visitors_to_cancel.action_cancel()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('station_id') and vals.get('appointment_type_id'):
                app_type = self.env['appointment.type'].browse(vals['appointment_type_id'])
                if app_type.station_id:
                    vals['station_id'] = app_type.station_id.id

        records = super().create(vals_list)
        
        # Link visitor if appointment was created via the quick book action
        for record in records:
            if record.visitor_id:
                record.visitor_id.write({'appointment_id': record.id})

        confirming_appointments = records.filtered(lambda r: r.state == 'confirmed')
        if confirming_appointments:
            confirming_appointments._create_frontdesk_visitors()
        return records

    def _create_frontdesk_visitors(self):
        fallback_station = False

        visitor_vals = []
        for appt in self:
            # Skip if this appointment already has a visitor linked
            if appt.visitor_id or self.env['frontdesk.visitor'].search_count([('appointment_id', '=', appt.id)]):
                continue

            station = appt.station_id
            if not station:
                if not fallback_station:
                    fallback_station = self.env['frontdesk.frontdesk'].search([('name', '=', 'Main Reception')], limit=1)
                    if not fallback_station:
                        fallback_station = self.env['frontdesk.frontdesk'].create({
                            'name': 'Main Reception',
                            'is_host': True,
                            'is_drink': True,
                        })
                station = fallback_station

            visitor_vals.append({
                'name': appt.partner_id.name or 'Visitor',
                'host_id': appt.staff_id.id if appt.staff_id else False,
                'expected_arrival': appt.start_datetime,
                'station_id': station.id,
                'state': 'planned',
                'appointment_id': appt.id,
                'email': appt.partner_id.email,
                'phone': appt.partner_id.phone or appt.partner_id.mobile,
                'company': appt.partner_id.parent_id.name or appt.partner_id.company_name,
                'partner_id': appt.partner_id.id,
            })

        if visitor_vals:
            self.env['frontdesk.visitor'].create(visitor_vals)
