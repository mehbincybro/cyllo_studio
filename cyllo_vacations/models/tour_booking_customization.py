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

class TourBookingCustomization(models.Model):
    _name = 'tour.booking.customization'
    _description = 'Tour Booking Customization'
    _order = 'option_id, id'

    name = fields.Char(string='Description', compute='_compute_name', store=True)
    booking_id = fields.Many2one('tour.booking', string='Booking', ondelete='cascade')
    inquiry_id = fields.Many2one('tour.inquiry', string='Inquiry', ondelete='cascade')
    option_id = fields.Many2one('tour.package.option', string='Option Category', required=True)
    option_line_id = fields.Many2one('tour.package.option.line', string='Selected Choice', required=True)
    price_extra = fields.Monetary(string='Extra Price', currency_field='currency_id')
    price_application = fields.Selection([
        ('per_booking', 'Per Booking'),
        ('per_person', 'Per Traveler'),
        ('per_adult', 'Per Adult'),
        ('per_child', 'Per Child'),
        ('per_infant', 'Per Infant'),
    ], string='Apply Price', default='per_booking', required=True)
    quantity = fields.Float(string='Quantity', compute='_compute_amount', store=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', compute='_compute_amount', store=True)
    currency_id = fields.Many2one('res.currency', related='option_id.package_id.currency_id', readonly=True)
    product_id = fields.Many2one('product.product', string='Sale Product')

    @api.depends('option_id.name', 'option_line_id.name')
    def _compute_name(self):
        for record in self:
            if record.option_id and record.option_line_id:
                record.name = _('%(option)s: %(choice)s') % {
                    'option': record.option_id.name,
                    'choice': record.option_line_id.name,
                }
            else:
                record.name = record.option_line_id.name or record.option_id.name

    @api.depends(
        'price_extra',
        'price_application',
        'booking_id.num_adults',
        'booking_id.num_children',
        'booking_id.num_infants',
        'inquiry_id.num_adults',
        'inquiry_id.num_children',
        'inquiry_id.num_infants',
    )
    def _compute_amount(self):
        for record in self:
            quantity = record._get_price_quantity()
            record.quantity = quantity
            record.amount = record.price_extra * quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._prepare_option_line_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._prepare_option_line_values(vals)
        return super().write(vals)

    @api.onchange('option_line_id')
    def _onchange_option_line_id(self):
        if self.option_line_id:
            self.price_extra = self.option_line_id.price_extra
            self.option_id = self.option_line_id.option_id
            self.price_application = self.option_line_id.price_application
            self.product_id = self.option_line_id.product_id

    @api.model
    def _prepare_option_line_values(self, vals):
        option_line = self.env['tour.package.option.line']
        if vals.get('option_line_id'):
            option_line = option_line.browse(vals['option_line_id'])
            if option_line.exists():
                vals.setdefault('option_id', option_line.option_id.id)
                vals.setdefault('price_extra', option_line.price_extra)
                vals.setdefault('price_application', option_line.price_application)
                vals.setdefault('product_id', option_line.product_id.id)
        return vals

    def _get_passenger_counts(self):
        self.ensure_one()
        source = self.booking_id or self.inquiry_id
        return {
            'adults': source.num_adults if source else 0,
            'children': source.num_children if source else 0,
            'infants': source.num_infants if source else 0,
            'total': source.total_persons if source else 0,
        }

    def _get_price_quantity(self):
        self.ensure_one()
        counts = self._get_passenger_counts()
        if self.price_application == 'per_person':
            return counts['total']
        if self.price_application == 'per_adult':
            return counts['adults']
        if self.price_application == 'per_child':
            return counts['children']
        if self.price_application == 'per_infant':
            return counts['infants']
        return 1

    def _get_document_product(self):
        self.ensure_one()
        package = self.option_id.package_id
        return self.product_id or self.option_line_id.product_id or package.product_id or self.env.ref(
            'cyllo_vacations.product_tour_booking',
            raise_if_not_found=False
        )

    def _get_sale_line_values(self):
        self.ensure_one()
        product = self._get_document_product()
        if not product or self.quantity <= 0:
            return False
        return {
            'product_id': product.id,
            'name': self.name,
            'product_uom_qty': self.quantity,
            'price_unit': self.price_extra,
        }

    def _get_invoice_line_values(self):
        self.ensure_one()
        product = self._get_document_product()
        if not product or self.quantity <= 0:
            return False
        return {
            'product_id': product.id,
            'name': self.name,
            'quantity': self.quantity,
            'price_unit': self.price_extra,
        }

    @api.constrains('booking_id', 'inquiry_id')
    def _check_linked_document(self):
        for record in self:
            if not record.booking_id and not record.inquiry_id:
                raise ValidationError(_('A customization must be linked to an inquiry or a booking.'))

    @api.constrains('booking_id', 'inquiry_id', 'option_id')
    def _check_package_match(self):
        for record in self:
            package = record.option_id.package_id
            if record.booking_id and record.booking_id.package_id != package:
                raise ValidationError(_('The selected customization option does not belong to the booking package.'))
            if record.inquiry_id and record.inquiry_id.package_id != package:
                raise ValidationError(_('The selected customization option does not belong to the inquiry package.'))

    @api.constrains('option_id', 'option_line_id')
    def _check_line_matches_option(self):
        for record in self:
            if record.option_line_id.option_id != record.option_id:
                raise ValidationError(_('The selected choice must belong to the selected option category.'))
