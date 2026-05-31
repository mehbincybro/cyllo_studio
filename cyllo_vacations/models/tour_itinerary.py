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


class TourItinerary(models.Model):
    _name = 'tour.itinerary'
    _description = 'Tour Itinerary'
    _order = 'package_id, day_number'
    
    name = fields.Char(string='Day Title', required=True, translate=True)
    day_number = fields.Integer(string='Day Number', required=True, default=1)
    package_id = fields.Many2one('tour.package', string='Package', required=True, 
                                  ondelete='cascade', index=True)
    description = fields.Html(string='Description', translate=True)
    activities = fields.Text(string='Activities', translate=True)
    # Timing
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    # Locations
    location = fields.Char(string='Location', translate=True)
    start_location = fields.Char(string='Start Location', translate=True)
    end_location = fields.Char(string='End Location', translate=True)
    # Services
    hotel_id = fields.Many2one('tour.hotel', string='Hotel')
    accommodation = fields.Char(string='Accommodation', translate=True,
                                 help='Accommodation details for this day')
    transportation_id = fields.Many2one('tour.transportation', string='Transportation')
    meal_ids = fields.Many2many('tour.meal', string='Meals')
    meals = fields.Char(string='Meals Included', translate=True,
                        help='Description of meals included (e.g., Breakfast, Lunch, Dinner)')
    attraction_ids = fields.Many2many('tour.attraction', string='Attractions')
    # Media
    image = fields.Image(string='Image')
    # Notes
    notes = fields.Text(string='Notes', translate=True)
    
    @api.constrains('day_number')
    def _check_day_number(self):
        for record in self:
            if record.day_number < 1:
                raise ValidationError(_('Day number must be positive.'))

