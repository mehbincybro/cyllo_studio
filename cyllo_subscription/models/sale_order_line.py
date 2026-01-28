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
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo import api, fields, models,_


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
    end_date = fields.Datetime(string='End Date')

    @api.onchange('time_based_price_id', 'product_uom_qty')
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """When a product is added default value to time_based_price_id field
        is the first value from the time-based-price model in products"""
        if self.product_template_id.time_based_ids:
            self.time_based_price_id = self.product_template_id.time_based_ids[0]

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

    @api.constrains('end_date')
    def _check_end_date(self):
        for record in self:
            if record.end_date and record.end_date < record.order_id.date_order:
                raise ValidationError(_("Invalid End Date: The subscription end date cannot be prior to the order date."))

