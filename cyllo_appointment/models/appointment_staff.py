# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _


class AppointmentStaff(models.Model):
    _name = 'appointment.staff'
    _description = 'Appointment Staff'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee',
        help='Link to HR employee record if available')
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    job_title = fields.Char(string='Job Title / Specialization')
    bio = fields.Text(string='Bio / Description')
    image = fields.Image(string='Photo', max_width=256, max_height=256)
    color = fields.Integer(string='Color Index', default=0)
    # Working hours
    working_hours_id = fields.Many2one(
        'resource.calendar', string='Working Hours',
        help='Staff member availability schedule'
    )
    # Linked appointment types
    appointment_type_ids = fields.Many2many(
        'appointment.type', 'appointment_type_staff_rel',
        'staff_id', 'type_id',
        string='Appointment Types'
    )
    # Notification preferences
    notify_on_new_appointment = fields.Boolean(
        string='Notify on New Appointment', default=True
    )
    notify_on_cancellation = fields.Boolean(
        string='Notify on Cancellation', default=True
    )
    notify_on_reschedule = fields.Boolean(
        string='Notify on Reschedule', default=True
    )
    # Stats
    appointment_count = fields.Integer(
        string='Total Appointments', compute='_compute_appointment_count'
    )
    upcoming_appointment_count = fields.Integer(
        string='Upcoming Appointments', compute='_compute_appointment_count'
    )

    @api.depends('name')
    def _compute_appointment_count(self):
        today = fields.Datetime.now()
        for rec in self:
            appointments = self.env['appointment.appointment'].search([
                ('staff_id', '=', rec.id)
            ])
            rec.appointment_count = len(appointments)
            rec.upcoming_appointment_count = len(appointments.filtered(
                lambda a: a.start_datetime >= today and a.state not in ('cancelled', 'rejected')
            ))

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            if not self.name:
                self.name = self.user_id.name
            if not self.email:
                self.email = self.user_id.email

    def action_view_upcoming_appointments(self):
        self.ensure_one()
        today = fields.Datetime.now()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upcoming Appointments - %s') % self.name,
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [
                ('staff_id', '=', self.id),
                ('start_datetime', '>=', today),
                ('state', 'not in', ['cancelled', 'rejected']),
            ],
            'context': {'default_staff_id': self.id},
        }

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments - %s') % self.name,
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('staff_id', '=', self.id)],
            'context': {'default_staff_id': self.id},
        }
