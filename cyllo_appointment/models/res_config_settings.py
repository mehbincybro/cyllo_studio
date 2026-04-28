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
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appointment_default_slot_interval = fields.Selection([
        ('15', '15 Minutes'),
        ('30', '30 Minutes'),
        ('45', '45 Minutes'),
        ('60', '1 Hour'),
        ('90', '1.5 Hours'),
        ('120', '2 Hours'),
    ], string='Default Slot Interval',
        config_parameter='cyllo_appointment.default_slot_interval',
        default='30'
    )
    appointment_default_min_booking_notice = fields.Float(
        string='Default Min. Booking Notice (hours)',
        config_parameter='cyllo_appointment.default_min_booking_notice',
        default=1.0,
        help='Default minimum hours in advance required for booking'
    )
    appointment_default_max_booking_days = fields.Integer(
        string='Default Max Booking Horizon (days)',
        config_parameter='cyllo_appointment.default_max_booking_days',
        default=60
    )
    appointment_send_confirmation = fields.Boolean(
        string='Send Confirmation Emails by Default',
        config_parameter='cyllo_appointment.send_confirmation',
        default=True
    )
    appointment_send_reminder = fields.Boolean(
        string='Send Reminder Emails by Default',
        config_parameter='cyllo_appointment.send_reminder',
        default=True
    )
    appointment_default_reminder_hours = fields.Char(
        string='Default Reminder Times (hours before)',
        config_parameter='cyllo_appointment.default_reminder_hours',
        default='24,2',
        help='Comma-separated hours before appointment. Example: 24,2'
    )
    appointment_send_followup = fields.Boolean(
        string='Send Follow-up Emails by Default',
        config_parameter='cyllo_appointment.send_followup',
        default=False
    )
    appointment_followup_hours = fields.Float(
        string='Default Follow-up After (hours)',
        config_parameter='cyllo_appointment.followup_hours',
        default=24.0
    )
    appointment_send_sms = fields.Boolean(
        string='Enable SMS Reminders',
        config_parameter='cyllo_appointment.send_sms',
        default=False
    )
    appointment_cancellation_policy = fields.Char(
        string='Cancellation Policy',
        config_parameter='cyllo_appointment.cancellation_policy',
        help='Displayed to customers when booking'
    )
