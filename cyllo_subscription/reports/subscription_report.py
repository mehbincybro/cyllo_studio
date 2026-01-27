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
from odoo import fields, models, tools


class SubscriptionReport(models.Model):
    """Model for the subscription report"""
    _name = 'subscription.report'
    _description = 'Subscription Report'
    _auto = False

    partner_id = fields.Many2one('res.partner', string='Customer',
                                 help='Name of the customer')
    subscription_order_line_ids = fields.One2many('subscription.order.line',
                                                  'subscription_order_id',
                                                  string='Order Line',
                                                  help='Subscription order line')
    state_subscription = fields.Selection(
        selection=[('quotation', 'Quotation'), ('active', 'Active'),
                   ('renew', 'Renew'), ('lost', 'Lost'),
                   ('trial', 'On Trial')], default='active',
        string='Subscription State', help='State of the subscription')
    time_based_price_id = fields.Many2one('time.based.price',
                                          string='Recurrence', required=True,
                                          help='Recurrence of the product')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('posted', 'Posted')], default='draft',
        help='State of the order')
    recurring_revenue = fields.Float(help='Monthly recurring revenue')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    weekly_price_sum = fields.Float(string='Weekly Recurring Revenue',
                                    help='Total revenue generated on a weekly basis from recurring charges, '
                                         'subscriptions, or contracts.')
    monthly_price_sum = fields.Float(string='Monthly Recurring Revenue',
                                     help='Total monthly revenue generated from recurring charges, subscriptions, '
                                          'or contracts.')
    yearly_price_sum = fields.Float(string='Yearly Recurring Revenue',
                                    help='Total annual revenue generated from recurring charges, '
                                         'subscriptions, or contracts.')
    number_of_product_sold = fields.Integer(string='Total Product Sold',
                                            help='Total sold product count')
    id = fields.Integer()

    def init(self):
        """Function fetch data to show on the report"""
        tools.drop_view_if_exists(self._cr, 'subscription_report')
        self._cr.execute("""
        CREATE OR REPLACE VIEW subscription_report AS SELECT 
        ROW_NUMBER() OVER (ORDER BY tbp.subscription_unit, so.state, so.state_subscription, tbp.id) AS id,
        tbp.subscription_unit, so.state AS state, so.state_subscription AS state_subscription,
        tbp.id AS time_based_price_id, sol.total_price, rp.id AS partner_id, 
        rc.id AS company_id, COUNT(*) AS order_count, SUM(sol.total_price) AS recurring_revenue, 
        SUM(CASE WHEN tbp.subscription_unit = 'weeks' THEN sol.total_price ELSE 0 END) AS weekly_price_sum, 
        SUM(CASE WHEN tbp.subscription_unit = 'months' THEN sol.total_price ELSE 0 END) AS monthly_price_sum, 
        SUM(CASE WHEN tbp.subscription_unit = 'years' THEN sol.total_price ELSE 0 END) AS yearly_price_sum, 
        pp.id AS product_id, COUNT(DISTINCT product_id) AS number_of_product_sold 
        FROM subscription_order so LEFT JOIN subscription_order_line sol ON so.id = sol.subscription_order_id 
        LEFT JOIN time_based_price tbp ON sol.time_based_price_id = tbp.id 
        LEFT JOIN res_partner rp ON so.partner_id = rp.id 
        LEFT JOIN res_company rc ON so.company_id = rc.id 
        LEFT JOIN product_product pp ON sol.product_id = pp.id 
        GROUP BY tbp.subscription_unit, sol.total_price, rp.id, rc.id, tbp.id, 
        so.state, so.state_subscription, pp.id;""")
