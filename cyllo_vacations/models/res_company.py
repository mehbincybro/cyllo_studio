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
from odoo import fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Tour Agency Settings
    tour_auto_create_lead = fields.Boolean(
        string='Auto Create CRM Lead from Inquiry',
        default=True,
        help='Automatically create a CRM lead when a tour inquiry is submitted'
    )
    tour_create_sale_order = fields.Boolean(
        string='Auto Create Sales Order from Booking',
        default=True,
        help='Automatically create a sales order when a booking is confirmed'
    )
    tour_create_calendar_event = fields.Boolean(
        string='Create Calendar Event for Bookings',
        default=True,
        help='Automatically create calendar events for tour bookings'
    )
    tour_require_payment = fields.Boolean(
        string='Require Payment for Booking',
        default=False,
        help='Require full or partial payment to confirm booking'
    )
    tour_minimum_payment_percent = fields.Float(
        string='Minimum Payment Percentage',
        default=0.0,
        help='Minimum payment percentage required to confirm booking (0-100)'
    )
    tour_cancellation_days = fields.Integer(
        string='Cancellation Notice Days',
        default=7,
        help='Minimum days notice required for cancellation'
    )
    tour_cancellation_fee_percent = fields.Float(
        string='Cancellation Fee Percentage',
        default=10.0,
        help='Cancellation fee as percentage of total amount'
    )
    tour_auto_confirm_booking = fields.Boolean(
        string='Auto Confirm Bookings',
        default=False,
        help='Automatically confirm bookings after payment'
    )
    tour_default_terms = fields.Html(
        string='Default Terms & Conditions',
        translate=True,
        help='Default terms and conditions for tour packages'
    )
    tour_default_cancellation_policy = fields.Html(
        string='Default Cancellation Policy',
        translate=True,
        help='Default cancellation policy for tour packages'
    )
