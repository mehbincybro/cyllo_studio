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

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


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

    @api.depends('time_based_price_id', 'product_uom_qty')
    def _compute_price_unit(self):
        """ Compute the unit price for subscription-based products.
        This method overrides the default price computation to look up
        specific time-based pricing rules from the pricelist. If no
        rule is found, it falls back to the plan's default cost."""
        super()._compute_price_unit()

        for line in self:
            if line.product_template_id.is_subscription and line.time_based_price_id:
                plan = line.time_based_price_id
                order = line.order_id
                time_based_price_rule = order.pricelist_id._get_time_based_price_rule(line.product_template_id.id,line.time_based_price_id.subscription_unit,line.time_based_price_id.duration,order.date_order,line.product_uom_qty)
                price = time_based_price_rule.fixed_price if time_based_price_rule else plan.cost
                price_unit = plan.currency_id._convert(
                    price,
                    order.pricelist_id.currency_id,
                    order.company_id,
                    order.date_order.date()
                )
                line.price_unit = price_unit

    @api.constrains('end_date')
    def _check_end_date(self):
        """Validate that the subscription end date is not in the past relative to the order date.
        raises ValidationError: If the end date is before the order creation date."""
        for record in self:
            if record.end_date and record.end_date < record.order_id.date_order:
                raise ValidationError(
                    _("Invalid End Date: The subscription end date cannot be prior to the order date."))

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
        if self.product_template_id.trial_period > 0:
            history_exists = self.env['subscription.trial.history'].search([
                ('partner_id', '=', self.order_id.partner_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if history_exists:
                self.trial_end = fields.Datetime.now()
            else:
                if self.product_template_id.unit == 'days':
                    self.trial_end = fields.Datetime.now() + relativedelta(days=self.product_template_id.trial_period)
                elif self.product_template_id.unit == 'weeks':
                    self.trial_end = fields.Datetime.now() + relativedelta(weeks=self.product_template_id.trial_period)
                elif self.product_template_id.unit == 'months':
                    self.trial_end = fields.Datetime.now() + relativedelta(months=self.product_template_id.trial_period)
                else:
                    self.trial_end = fields.Datetime.now()
        else:
            self.trial_end = fields.Datetime.now()


