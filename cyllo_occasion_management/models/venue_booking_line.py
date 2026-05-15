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
from odoo import api, fields, models


class VenueBookingLine(models.Model):
    """Model to manage the Venue Booking lines of the Venue Reservation"""
    _name = 'venue.booking.line'
    _description = "Venue Booking Lines"

    venue_booking_id = fields.Many2one('venue.booking',
                                       string="Venue Booking",
                                       help='The relation added for the venue '
                                            'Booking ')
    state = fields.Selection([('done', 'Done'), ('pending', 'Pending')],
                             string="State", default="pending",
                             readonly=True,
                             help="The state of the venue Booking line")
    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self:
                                  self.env.user.company_id.currency_id,
                                  string="Currency",
                                  help="The currency of the booking line")
    is_invoiced = fields.Boolean(string="Invoiced", readonly=True,
                                 help="The boolean value used for finding the "
                                      "venue booking is invoiced or not")
    venue_type_id = fields.Many2one('venue.type',
                                    string="Related Venue Type",
                                    related='venue_booking_id.venue_type_id',
                                    help="The venue type of the booking line")
    amenity_id = fields.Many2one('amenities', string='Amenities',
                                 help='The relational field for the booking '
                                      'line with the amenities model')
    quantity = fields.Float(string="Quantity", default=1,
                            help="Quantity of the Amenities")
    amount = fields.Float(string="Amount", help="Amount of the Amenities",
                          related='amenity_id.amount')
    sub_total = fields.Float(string="Sub Total",
                             compute="_compute_extra_sub_total",
                             readonly=True, help="Sub Total of the Values")
    is_included = fields.Boolean(string="Is Included Amenity",
                                 default=False)
    allowed_amenity_ids = fields.Many2many('amenities', compute='_compute_allowed_amenity_ids',
                                           help="Technical field to store allowed amenities for the selected venue")

    @api.depends('venue_booking_id.venue_id')
    def _compute_allowed_amenity_ids(self):
        """Compute allowed amenities based on the selected venue in parent booking."""
        for line in self:
            if line.venue_booking_id.venue_id:
                line.allowed_amenity_ids = line.venue_booking_id.venue_id.venue_line_ids.mapped('amenities_id')
            else:
                line.allowed_amenity_ids = self.env['amenities'].search([])

    @api.depends('quantity', 'amount')
    def _compute_extra_sub_total(self):
        """Compute function for the Amenities"""
        for booking in self:
            booking.sub_total = booking.quantity * booking.amount
