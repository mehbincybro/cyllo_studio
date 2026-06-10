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

class TourPackageOptionLine(models.Model):
    _name = 'tour.package.option.line'
    _description = 'Tour Package Option Line'
    _order = 'sequence, id'

    name = fields.Char(string='Choice Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    option_id = fields.Many2one('tour.package.option', string='Option', required=True, ondelete='cascade')
    description = fields.Text(string='Description', translate=True)
    price_extra = fields.Monetary(string='Extra Price', currency_field='currency_id', help="Additional cost for this option")
    price_application = fields.Selection([
        ('per_booking', 'Per Booking'),
        ('per_person', 'Per Traveler'),
        ('per_adult', 'Per Adult'),
        ('per_child', 'Per Child'),
        ('per_infant', 'Per Infant'),
    ], string='Apply Price', default='per_booking', required=True)
    currency_id = fields.Many2one('res.currency', related='option_id.package_id.currency_id', readonly=True)
    is_default = fields.Boolean(string='Is Default', default=False, help="Set as default choice. Only one choice per option should be default.")
    hotel_id = fields.Many2one('tour.hotel', string='Hotel')
    room_type_id = fields.Many2one('tour.hotel.room.type', string='Room Type')
    transportation_id = fields.Many2one('tour.transportation', string='Transportation')
    meal_id = fields.Many2one('tour.meal', string='Meal')
    attraction_id = fields.Many2one('tour.attraction', string='Attraction')
    product_id = fields.Many2one(
        'product.product',
        string='Sale Product',
        help='Product used on quotations and invoices for this customization line. '
             'If empty, the tour package product is used.'
    )

    @api.onchange('hotel_id', 'transportation_id', 'meal_id', 'attraction_id')
    def _onchange_service_id(self):
        for record in self:
            service = record.hotel_id or record.transportation_id or record.meal_id or record.attraction_id
            if service and not record.product_id:
                record.product_id = getattr(service, 'product_id', False)
            if service and not record.name:
                record.name = service.name

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered('is_default')._unset_other_defaults()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default'):
            self.filtered('is_default')._unset_other_defaults()
        return res

    def _unset_other_defaults(self):
        for record in self:
            self.search([
                ('option_id', '=', record.option_id.id),
                ('is_default', '=', True),
                ('id', '!=', record.id),
            ]).write({'is_default': False})

    @api.constrains('room_type_id', 'hotel_id')
    def _check_room_type_hotel(self):
        for record in self:
            if record.room_type_id and record.hotel_id and record.room_type_id.hotel_id != record.hotel_id:
                raise ValidationError(_('The selected room type must belong to the selected hotel.'))
