# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

class TransportBooking(models.Model):
    """Model to manage transportation logistics for events and venue bookings"""
    _name = 'transport.booking'
    _description = 'Transport Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    max_capacity = fields.Integer(related='vehicle_id.max_capacity', string="Max Capacity", readonly=True)
    booked_capacity = fields.Integer(string="Booked Capacity", required=True, help="Number of persons booked")
    driver_id = fields.Many2one('res.partner', string="Driver", compute='_compute_driver_id', store=True, readonly=False)
    
    event_id = fields.Many2one('event.event', string="Event")
    venue_booking_id = fields.Many2one('venue.booking', string="Venue Booking")
    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], string="Status", default='draft', tracking=True)

    daily_rate = fields.Float(string="Daily Rate", compute='_compute_daily_rate', store=True, readonly=False)
    total_amount = fields.Float(string="Total Amount", compute='_compute_total_amount', store=True)

    @api.depends('vehicle_id')
    def _compute_daily_rate(self):
        """Compute default daily rate from selected vehicle"""
        for record in self:
            if record.vehicle_id:
                record.daily_rate = record.vehicle_id.daily_charge
            else:
                record.daily_rate = 0.0

    @api.depends('start_date', 'end_date', 'daily_rate')
    def _compute_total_amount(self):
        """Calculate total amount based on duration and daily rate"""
        for record in self:
            if record.start_date and record.end_date:
                diff = record.end_date - record.start_date
                days = diff.days + 1  # Standard duration calculation
                if diff.seconds > 0: # If there's partial day
                    # Actually Odoo usually calculates days as ceil(seconds / 86400) or similar.
                    # I'll stick to simple days diff + 1 for now or 0 if end < start.
                    pass
                days = max(1, days)
                record.total_amount = days * record.daily_rate
            else:
                record.total_amount = 0.0

    def action_confirm(self):
        """Action to confirm the transport booking"""
        for record in self:
            record.state = 'confirm'

    @api.depends('vehicle_id')
    def _compute_driver_id(self):
        """Auto-populate driver from the selected vehicle"""
        for record in self:
            if record.vehicle_id:
                record.driver_id = record.vehicle_id.driver_id
            else:
                record.driver_id = False

    @api.constrains('booked_capacity', 'vehicle_id')
    def _check_capacity(self):
        """Validate that booked capacity does not exceed vehicle limit"""
        for record in self:
            if record.vehicle_id and record.booked_capacity > record.max_capacity:
                raise ValidationError(_("Booked capacity (%s) cannot exceed vehicle maximum capacity (%s).") % (record.booked_capacity, record.max_capacity))

    @api.constrains('start_date', 'end_date', 'vehicle_id')
    def _check_vehicle_availability(self):
        """Check for vehicle scheduling conflicts to prevent double-booking"""
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError(_("Start Date must be before End Date."))
                
                domain = [
                    ('id', '!=', record.id),
                    ('vehicle_id', '=', record.vehicle_id.id),
                    ('start_date', '<', record.end_date),
                    ('end_date', '>', record.start_date),
                ]
                overlapping_bookings = self.search(domain)
                if overlapping_bookings:
                    raise ValidationError(_("This vehicle is already booked for the selected time period in %s.") % overlapping_bookings[0].name)

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequential code on creation"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('transport.booking') or _('New')
        return super().create(vals_list)
