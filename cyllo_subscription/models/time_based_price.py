# -*- coding: utf-8 -*-
from odoo import fields, models


class TimeBasedPrice(models.Model):
    """Model for time-based pricing"""
    _name = "time.based.price"
    _description = 'Time Based Price'

    name = fields.Char(string='Subscription Name', required=True, help='Subscription reference number')
    subscription_unit = fields.Selection(
        selection=[('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years')], required=True, string='Unit',
        help='Unit for the subscription')
    duration = fields.Integer(help='Duration of the subscription')
    currency_id = fields.Many2one('res.currency', string='Company Currency', required=True,
                                  help="Currency of current company",
                                  default=lambda self: self.env.user.company_id.currency_id)
    cost = fields.Monetary(string='Price', help='Cost of the product')
    product_template_id = fields.Many2one('product.template', string='Product', help='Product id store here')
