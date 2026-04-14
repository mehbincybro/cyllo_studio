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
from odoo.exceptions import ValidationError
from datetime import timedelta


class AppointmentSlot(models.Model):
    _name = 'appointment.slot'
    _description = 'Appointment Slot'
    _order = 'start_datetime'

    name = fields.Char(string='Slot Name', compute='_compute_name', store=True)
    appointment_type_id = fields.Many2one(
        'appointment.type', string='Appointment Type', required=True, ondelete='cascade'
    )
    staff_id = fields.Many2one('appointment.staff', string='Staff Member')
    resource_id = fields.Many2one('appointment.resource', string='Resource')
    start_datetime = fields.Datetime(string='Start', required=True)
    end_datetime = fields.Datetime(string='End', required=True, compute='_compute_end_datetime', store=True, readonly=False)
    duration = fields.Float(string='Duration (hours)', related='appointment_type_id.duration')
    max_attendees = fields.Integer(
        string='Max Attendees', related='appointment_type_id.max_attendees', store=True
    )
    booked_count = fields.Integer(
        string='Booked', compute='_compute_booked_count'
    )
    available_count = fields.Integer(
        string='Available Spots', compute='_compute_booked_count'
    )
    is_available = fields.Boolean(
        string='Available', compute='_compute_booked_count', store=False
    )
    state = fields.Selection([
        ('available', 'Available'),
        ('partially_booked', 'Partially Booked'),
        ('fully_booked', 'Fully Booked'),
        ('blocked', 'Blocked'),
    ], string='Status', compute='_compute_booked_count', store=True)
    appointment_ids = fields.One2many(
        'appointment.appointment', 'slot_id', string='Appointments'
    )

    @api.depends('start_datetime', 'appointment_type_id.name')
    def _compute_name(self):
        for rec in self:
            if rec.start_datetime and rec.appointment_type_id:
                rec.name = f"{rec.appointment_type_id.name} - {fields.Datetime.to_string(rec.start_datetime)}"
            else:
                rec.name = _('New Slot')

    @api.depends('start_datetime', 'duration')
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration:
                rec.end_datetime = rec.start_datetime + timedelta(hours=rec.duration)
            else:
                rec.end_datetime = rec.start_datetime

    @api.depends('appointment_ids', 'appointment_ids.state', 'appointment_ids.attendee_count', 'max_attendees')
    def _compute_booked_count(self):
        for rec in self:
            active_appointments = rec.appointment_ids.filtered(
                lambda a: a.state not in ('cancelled', 'rejected')
            )
            rec.booked_count = sum(active_appointments.mapped('attendee_count'))
            rec.available_count = max(0, rec.max_attendees - rec.booked_count)
            rec.is_available = rec.available_count > 0
            if rec.booked_count == 0:
                rec.state = 'available'
            elif rec.booked_count >= rec.max_attendees:
                rec.state = 'fully_booked'
            else:
                rec.state = 'partially_booked'

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                if rec.end_datetime <= rec.start_datetime:
                    raise ValidationError(_('End time must be after start time.'))
