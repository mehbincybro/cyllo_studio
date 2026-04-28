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


class AppointmentType(models.Model):
    _name = 'appointment.type'
    _description = 'Appointment Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index', default=0)
    description = fields.Html(string='Description')
    category = fields.Selection([
        ('consultation', 'Consultation'),
        ('service', 'Service'),
        ('meeting', 'Meeting'),
        ('class', 'Class / Training'),
        ('event', 'Event'),
        ('other', 'Other'),
    ], string='Category', default='service', required=True, tracking=True)
    scheduling_type = fields.Selection([
        ('dynamic', 'Dynamic (Based on Working Hours)'),
        ('predefined', 'Predefined Slots'),
    ], string='Scheduling Method', default='dynamic', required=True)
    # Payment / Pricing
    is_paid = fields.Boolean(string='Is Paid Appointment', default=False)
    product_id = fields.Many2one('product.product', string='Service Product',
                                 domain=[('type', '=', 'service')],
                                 help='The service product used for billing the appointment')
    # Duration & Slot Configuration
    duration = fields.Float(string='Duration (hours)', default=1.0,
                            required=True)
    slot_interval = fields.Selection([
        ('15', '15 Minutes'),
        ('30', '30 Minutes'),
        ('45', '45 Minutes'),
        ('60', '1 Hour'),
        ('90', '1.5 Hours'),
        ('120', '2 Hours'),
    ], string='Slot Interval', default='30', required=True)
    min_booking_notice = fields.Float(string='Minimum Booking Notice (hours)',
                                      default=1.0,
                                      help='Minimum hours required in advance for booking an appointment')
    max_booking_days = fields.Integer(string='Max Booking Horizon (days)',
                                      default=60,
                                      help='How many days in advance can an appointment be booked')
    # Rescheduling
    allow_reschedule = fields.Boolean(string='Allow Rescheduling', default=True)
    reschedule_deadline_hours = fields.Float(
        string='Reschedule Deadline (hours)', default=24.0,
        help='Hours before appointment when rescheduling is no longer allowed')
    # Cancellation
    allow_cancel = fields.Boolean(string='Allow Cancellation from Website',
                                  default=True)
    cancel_deadline_hours = fields.Float(string='Cancel Deadline (hours)',
                                         default=24.0,
                                         help='Hours before appointment when online cancellation is no longer allowed')
    # Capacity
    max_attendees = fields.Integer(string='Max Attendees per Slot', default=1)
    # Location
    location_type = fields.Selection([
        ('physical', 'Physical Location'),
        ('online', 'Online / Video Call'),
        ('phone', 'Phone Call'),
        ('custom', 'Custom'),
    ], string='Location Type', default='physical')
    location = fields.Char(string='Location / URL')
    # Resources & Staff
    resource_ids = fields.Many2many(
        'appointment.resource', 'appointment_type_resource_rel',
        'type_id', 'resource_id',
        string='Resources'
    )
    staff_ids = fields.Many2many(
        'appointment.staff', 'appointment_type_staff_rel',
        'type_id', 'staff_id',
        string='Staff Members'
    )
    require_resource = fields.Boolean(string='Resource Required', default=False)
    require_staff = fields.Boolean(string='Staff Assignment Required',
                                   default=True)
    # Working Hours
    working_hours_id = fields.Many2one(
        'resource.calendar', string='Working Hours',
        help='Define the availability schedule for this appointment type'
    )
    # Notification Settings
    send_confirmation = fields.Boolean(string='Send Confirmation Email',
                                       default=True)
    confirmation_template_id = fields.Many2one(
        'mail.template', string='Confirmation Email Template',
        domain=[('model', '=', 'appointment.appointment')]
    )
    send_whatsapp_confirmation = fields.Boolean(
        string='Send WhatsApp Confirmation', default=False)
    whatsapp_confirmation_template_id = fields.Many2one(
        'whatsapp.template', string='WhatsApp Confirmation Template',
        domain=[('model_id.model', '=', 'appointment.appointment')]
    )
    send_reminder = fields.Boolean(string='Send Reminders', default=True)
    reminder_hours_before = fields.Char(
        string='Reminder Times (hours before)',
        default='24,2',
        help='Comma-separated hours before appointment to send reminders (e.g., 24,2)'
    )
    reminder_template_id = fields.Many2one(
        'mail.template', string='Reminder Email Template',
        domain=[('model', '=', 'appointment.appointment')]
    )
    send_sms_reminder = fields.Boolean(string='Send SMS Reminders',
                                       default=False)
    sms_reminder_template_id = fields.Many2one(
        'sms.template', string='SMS Reminder Template',
        domain=[('model', '=', 'appointment.appointment')]
    )
    send_whatsapp_reminder = fields.Boolean(string='Send WhatsApp Reminders',
                                            default=False)
    whatsapp_reminder_template_id = fields.Many2one(
        'whatsapp.template', string='WhatsApp Reminder Template',
        domain=[('model_id.model', '=', 'appointment.appointment')]
    )
    send_followup = fields.Boolean(string='Send Follow-up', default=False)
    followup_hours_after = fields.Float(string='Follow-up After (hours)',
                                        default=24.0)
    followup_template_id = fields.Many2one(
        'mail.template', string='Follow-up Email Template',
        domain=[('model', '=', 'appointment.appointment')]
    )
    send_whatsapp_followup = fields.Boolean(string='Send WhatsApp Follow-up',
                                            default=False)
    whatsapp_followup_template_id = fields.Many2one(
        'whatsapp.template', string='WhatsApp Follow-up Template',
        domain=[('model_id.model', '=', 'appointment.appointment')]
    )
    send_cancellation = fields.Boolean(string='Send Cancellation Email',
                                       default=True)
    cancellation_template_id = fields.Many2one(
        'mail.template', string='Cancellation Email Template',
        domain=[('model', '=', 'appointment.appointment')]
    )
    send_whatsapp_cancellation = fields.Boolean(
        string='Send WhatsApp Cancellation', default=False)
    whatsapp_cancellation_template_id = fields.Many2one(
        'whatsapp.template', string='WhatsApp Cancellation Template',
        domain=[('model_id.model', '=', 'appointment.appointment')]
    )
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_appointment_count'
    )
    upcoming_appointment_count = fields.Integer(
        string='Upcoming', compute='_compute_appointment_count'
    )

    def _compute_website_url(self):
        super(AppointmentType, self)._compute_website_url()
        for rec in self:
            if rec.id:
                rec.website_url = '/appointment/%s' % rec.id

    @api.depends('name')
    def _compute_appointment_count(self):
        today = fields.Datetime.now()
        for rec in self:
            appointments = self.env['appointment.appointment'].search([
                ('appointment_type_id', '=', rec.id)
            ])
            rec.appointment_count = len(appointments)
            rec.upcoming_appointment_count = len(appointments.filtered(
                lambda a: a.start_datetime >= today and a.state not in (
                    'cancelled', 'rejected')
            ))

    @api.constrains('duration', 'slot_interval')
    def _check_duration(self):
        for rec in self:
            if rec.duration <= 0:
                raise ValidationError(_('Duration must be positive.'))

    @api.constrains('min_booking_notice')
    def _check_min_booking_notice(self):
        for rec in self:
            if rec.min_booking_notice < 0:
                raise ValidationError(
                    _('Minimum booking notice cannot be negative.'))

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments - %s') % self.name,
            'res_model': 'appointment.appointment',
            'view_mode': 'list,form,calendar',
            'domain': [('appointment_type_id', '=', self.id)],
            'context': {'default_appointment_type_id': self.id},
        }
