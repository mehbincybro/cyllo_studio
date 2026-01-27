# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    """Inherited the model to add some fields and methods"""
    _inherit = 'sale.order.line'

    time_based_price_id = fields.Many2one('time.based.price', string='Time Based Pricing',
                                          default=lambda self: self.product_template_id.time_based_ids[0]
                                          if self.product_template_id.time_based_ids else False,
                                          domain="[('product_template_id', 'in', [product_template_id])]",
                                          help='Field shows the recurrence of the product')
    renewal_date = fields.Datetime(help='Renewal date for the subscription order created from this line')
    trial_end = fields.Datetime(help='Trial end date for the subscription order created from this line.')

    @api.onchange('time_based_price_id')
    def _onchange_time_based_price_id(self):
        """Change price when change the time-based pricing"""
        self.price_unit = self.time_based_price_id.cost
        self.check_trial_period()
        if self.time_based_price_id:
            if self.time_based_price_id.subscription_unit == 'weeks':
                self.renewal_date = fields.Datetime.now() + relativedelta(weeks=self.time_based_price_id.duration)
            elif self.time_based_price_id.subscription_unit == 'months':
                self.renewal_date = fields.Datetime.now() + relativedelta(months=self.time_based_price_id.duration)
            elif self.time_based_price_id.subscription_unit == 'years':
                self.renewal_date = fields.Datetime.now() + relativedelta(years=self.time_based_price_id.duration)

    def check_trial_period(self):
        """Check if any trial-period is added in product template"""
        if self.product_template_id.unit == 'days':
            self.trial_end = fields.Datetime.now() + relativedelta(days=self.product_template_id.trial_period)
        elif self.product_template_id.unit == 'weeks':
            self.trial_end = fields.Datetime.now() + relativedelta(weeks=self.product_template_id.trial_period)
        elif self.product_template_id.unit == 'months':
            self.trial_end = fields.Datetime.now() + relativedelta(months=self.product_template_id.trial_period)
        else:
            self.trial_end = fields.Datetime.now()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """When a product is added default value to time_based_price_id field
        is the first value from the time-based-price model in products"""
        if self.product_template_id.time_based_ids:
            self.time_based_price_id = self.product_template_id.time_based_ids[0]
