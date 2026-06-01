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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    tour_auto_create_lead = fields.Boolean(
        related='company_id.tour_auto_create_lead',
        readonly=False,
        string='Auto Create CRM Lead from Inquiry'
    )
    tour_create_sale_order = fields.Boolean(
        related='company_id.tour_create_sale_order',
        readonly=False,
        string='Auto Create Sales Order from Booking'
    )
    tour_create_calendar_event = fields.Boolean(
        related='company_id.tour_create_calendar_event',
        readonly=False,
        string='Create Calendar Event for Bookings'
    )
    tour_require_payment = fields.Boolean(
        related='company_id.tour_require_payment',
        readonly=False,
        string='Require Payment for Booking'
    )
    tour_minimum_payment_percent = fields.Float(
        related='company_id.tour_minimum_payment_percent',
        readonly=False,
        string='Minimum Payment Percentage'
    )
    tour_cancellation_days = fields.Integer(
        related='company_id.tour_cancellation_days',
        readonly=False,
        string='Cancellation Notice Days'
    )
    tour_cancellation_fee_percent = fields.Float(
        related='company_id.tour_cancellation_fee_percent',
        readonly=False,
        string='Cancellation Fee Percentage'
    )
    tour_auto_confirm_booking = fields.Boolean(
        related='company_id.tour_auto_confirm_booking',
        readonly=False,
        string='Auto Confirm Bookings'
    )
    tour_default_terms = fields.Html(
        related='company_id.tour_default_terms',
        readonly=False,
        string='Default Terms & Conditions'
    )
    tour_default_cancellation_policy = fields.Html(
        related='company_id.tour_default_cancellation_policy',
        readonly=False,
        string='Default Cancellation Policy'
    )

