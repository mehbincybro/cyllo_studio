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


class TourHotel(models.Model):
    _name = 'tour.hotel'
    _description = 'Tour Hotel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(string='Hotel Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Hotel Code', copy=False)
    active = fields.Boolean(default=True, tracking=True)
    # Location
    location = fields.Char(string='Location', help='City, Country')
    address = fields.Char(string='Full Address')
    # Contact Information
    partner_id = fields.Many2one('res.partner', string='Partner')
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='Zip')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    # Hotel Details
    hotel_type = fields.Selection([
        ('resort', 'Resort'),
        ('boutique', 'Boutique Hotel'),
        ('hostel', 'Hostel'),
        ('guest_house', 'Guest House'),
        ('apartment', 'Apartment'),
    ], string='Hotel Type', default='resort')
    star_rating = fields.Integer(string='Star Rating', help='Hotel star rating (1-5)')
    rating = fields.Float(string='Rating', digits=(2, 1))
    # Check-in/Check-out
    check_in_time = fields.Float(string='Check-in Time', help='Check-in time in 24h format (e.g., 15.0 for 3:00 PM)')
    check_out_time = fields.Float(string='Check-out Time', help='Check-out time in 24h format (e.g., 12.0 for 12:00 PM)')
    # Room Types
    room_type_ids = fields.One2many('tour.hotel.room.type', 'hotel_id', string='Room Types')
    # Amenities
    amenity_ids = fields.Many2many('tour.hotel.amenity', string='Amenities')
    # Description
    description = fields.Html(string='Description', translate=True)
    # Images
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    image_512 = fields.Image(related='image_1920', max_width=512, max_height=512, store=True)
    # Pricing
    price_per_night = fields.Monetary(string='Price per Night', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    # Product Link for invoicing
    product_id = fields.Many2one('product.product', string='Product',
                                  help='Product used for invoicing this hotel service')
    # Notes
    notes = fields.Text(string='Notes')
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('tour.hotel') or _('New')
        return super().create(vals_list)
