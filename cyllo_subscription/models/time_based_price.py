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
from odoo import fields, models


class TimeBasedPrice(models.Model):
    """Model for time-based pricing"""
    _name = "time.based.price"
    _description = 'Time Based Price'

    name = fields.Char(string='Subscription Name', required=True,
                       help='Subscription reference number')
    subscription_unit = fields.Selection(
        selection=[('weeks', 'Weeks'), ('months', 'Months'),
                   ('years', 'Years')], required=True, string='Unit',
        help='Unit for the subscription')
    duration = fields.Integer(help='Duration of the subscription')
    currency_id = fields.Many2one('res.currency', string='Company Currency',
                                  required=True,
                                  help="Currency of current company",
                                  default=lambda
                                      self: self.env.user.company_id.currency_id)
    cost = fields.Monetary(string='Price', help='Cost of the product')
    product_template_id = fields.Many2one('product.template', string='Product',
                                          help='Product id store here')
