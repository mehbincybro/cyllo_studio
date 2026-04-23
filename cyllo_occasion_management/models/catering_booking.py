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
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _

class CateringBooking(models.Model):
    """Model to manage dietary and banqueting requirements for events"""
    _name = 'catering.booking'
    _description = 'Catering Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: 'New')
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)
    platter_type_id = fields.Many2one('platter.type', string="Platter Type", required=True)
    guest_count = fields.Integer(string="Number of Guests", default=1)
    total_amount = fields.Float(string="Total Amount", compute='_compute_total_amount', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], string="Status", default='draft', tracking=True)

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        """Validate that the catering event start date is before the end date"""
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError(_("The Start Date cannot be greater than the End Date."))

    @api.depends('guest_count', 'platter_type_id.amount_per_person')
    def _compute_total_amount(self):
        """Calculate the total catering cost based on guest count and platter rate"""
        for record in self:
            record.total_amount = record.guest_count * record.platter_type_id.amount_per_person

    event_id = fields.Many2one('event.event', string="Event")
    venue_booking_id = fields.Many2one('venue.booking', string="Venue Booking")

    def action_confirm(self):
        """Confirm the catering order and move it to the hospitality queue"""
        self.state = 'confirm'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate sequential reference number on creation"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('catering.booking') or 'New'
        return super().create(vals_list)
