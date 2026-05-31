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


class TourHotelRoomType(models.Model):
    _name = 'tour.hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'sequence, name'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Room Type', required=True, translate=True)
    hotel_id = fields.Many2one('tour.hotel', string='Hotel', required=True,
                               ondelete='cascade')
    description = fields.Text(string='Description', translate=True)
    capacity = fields.Integer(string='Capacity', default=2)
    price_per_night = fields.Monetary(string='Price per Night',
                                      currency_field='currency_id')
    currency_id = fields.Many2one(related='hotel_id.currency_id',
                                  string='Currency', readonly=True)
    image = fields.Image(string='Image')