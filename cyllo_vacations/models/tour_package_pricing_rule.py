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


class TourPackagePricingRule(models.Model):
    _name = 'tour.package.pricing.rule'
    _description = 'Tour Package Pricing Rule'
    _order = 'sequence, id'

    package_id = fields.Many2one('tour.package', string='Tour Package', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Rule Name', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True)
    
    rule_type = fields.Selection([
        ('seasonal', 'Seasonal Price Multiplier'),
        ('group_size', 'Group Size Discount'),
        ('early_bird', 'Early-bird Discount')
    ], string='Rule Type', required=True, default='seasonal')

    # Seasonal rule fields
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    factor = fields.Float(string='Factor (Multiplier)', default=1.0, 
                         help='Multiply price by this factor. E.g., 1.15 to markup by 15%, or 0.90 for a 10% discount.')

    # Group size rule fields
    min_group = fields.Integer(string='Min Group Size', default=1)
    max_group = fields.Integer(string='Max Group Size', default=999)

    # Early-bird rule fields
    days_before = fields.Integer(string='Days Before Travel', default=30,
                                 help='Apply rule if travel start date is at least this many days after the booking confirmation/creation date.')

    # Discount fields for group_size and early_bird rules
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ], string='Discount Type', default='percentage')
    discount_value = fields.Float(string='Discount Value', default=0.0)

    @api.constrains('valid_from', 'valid_to')
    def _check_dates(self):
        for rule in self:
            if rule.rule_type == 'seasonal' and rule.valid_from and rule.valid_to:
                if rule.valid_to < rule.valid_from:
                    raise ValidationError(_('Valid To date must be after Valid From date.'))

    @api.constrains('min_group', 'max_group')
    def _check_group_limits(self):
        for rule in self:
            if rule.rule_type == 'group_size':
                if rule.min_group < 0 or rule.max_group < 0:
                    raise ValidationError(_('Group size limits cannot be negative.'))
                if rule.max_group < rule.min_group:
                    raise ValidationError(_('Max Group Size must be greater than or equal to Min Group Size.'))

    @api.constrains('factor')
    def _check_factor(self):
        for rule in self:
            if rule.rule_type == 'seasonal' and rule.factor <= 0:
                raise ValidationError(_('Seasonal factor must be strictly positive.'))

    @api.constrains('discount_value')
    def _check_discount_value(self):
        for rule in self:
            if rule.rule_type in ['group_size', 'early_bird']:
                if rule.discount_value < 0:
                    raise ValidationError(_('Discount value cannot be negative.'))
                if rule.discount_type == 'percentage' and rule.discount_value > 100:
                    raise ValidationError(_('Percentage discount cannot be greater than 100%.'))
