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
    
    # Revenue Metrics
    arr = fields.Float(string='ARR', 
                      help='Annual Recurring Revenue (ARR = MRR × 12)')
    nrr = fields.Float(string='NRR',
                      help='Non-Recurring Revenue (one-time charges)')
    mrr_change = fields.Float(string='MRR Change',
                             help='Change in MRR from previous period')
    arr_change = fields.Float(string='ARR Change',
                             help='Change in ARR from previous period')
    
    # Subscription Metrics
    subscription_count = fields.Integer(string='Subscription Count',
                                       help='Total number of subscriptions')
    active_subscription_count = fields.Integer(string='Active Subscriptions',
                                              help='Count of active subscriptions')
    trial_subscription_count = fields.Integer(string='Trial Subscriptions',
                                             help='Count of trial subscriptions')
    churned_subscription_count = fields.Integer(string='Churned Subscriptions',
                                               help='Count of churned subscriptions')
    new_subscription_count = fields.Integer(string='New Subscriptions',
                                           help='Count of new subscriptions in period')
    
    # Customer Metrics
    customer_count = fields.Integer(string='Customer Count',
                                   help='Unique customer count')
    new_customer_count = fields.Integer(string='New Customers',
                                       help='New customers in period')
    churned_customer_count = fields.Integer(string='Churned Customers',
                                           help='Customers who churned in period')
    
    # Performance Metrics
    churn_rate = fields.Float(string='Churn Rate (%)',
                             help='Percentage of subscriptions churned')
    retention_rate = fields.Float(string='Retention Rate (%)',
                                 help='Percentage of subscriptions retained')
    
    # Date Fields for Analysis
    start_date = fields.Datetime(string='Start Date',
                                 help='Subscription start date')
    next_invoice_date = fields.Datetime(string='Next Invoice Date',
                                       help='Next invoice date')
    end_date = fields.Datetime(string='End Date',
                              help='Subscription end date')
    trial_end_date = fields.Datetime(string='Trial End Date',
                                    help='Trial end date')
    
    # Product/Plan Metrics
    product_name = fields.Char(string='Product',
                              help='Product name for easier grouping')
    plan_name = fields.Char(string='Plan',
                           help='Subscription plan name')
    recurrence_name = fields.Char(string='Recurrence',
                                 help='Recurrence period name')

    def init(self):
        """Function fetch data to show on the report"""
        tools.drop_view_if_exists(self._cr, 'subscription_report')
        self._cr.execute("""
        CREATE OR REPLACE VIEW subscription_report AS 
        WITH subscription_data AS (
            SELECT 
                so.id AS subscription_id,
                so.partner_id,
                so.company_id,
                so.state,
                so.state_subscription,
                so.time_based_price_id,
                so.sale_order_template_id,
                so.renewal_date AS next_invoice_date,
                so.end_date,
                so.trial_end AS trial_end_date,
                so.create_date AS start_date,
                tbp.id AS time_based_price_id_val,
                tbp.subscription_unit,
                tbp.name AS recurrence_name,
                sol.product_id,
                sol.total_price,
                sol.subtotal,
                pt.name AS product_name,
                sot.name AS plan_name,
                CASE 
                    WHEN so.state_subscription = 'active' THEN 1 
                    ELSE 0 
                END AS is_active,
                CASE 
                    WHEN so.state_subscription = 'trial' THEN 1 
                    ELSE 0 
                END AS is_trial,
                CASE 
                    WHEN so.state_subscription = 'churned' THEN 1 
                    ELSE 0 
                END AS is_churned
            FROM subscription_order so
            LEFT JOIN subscription_order_line sol ON so.id = sol.subscription_order_id
            LEFT JOIN time_based_price tbp ON so.time_based_price_id = tbp.id
            LEFT JOIN res_partner rp ON so.partner_id = rp.id
            LEFT JOIN res_company rc ON so.company_id = rc.id
            LEFT JOIN product_product pp ON sol.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN sale_order_template sot ON so.sale_order_template_id = sot.id
        )
        SELECT 
            ROW_NUMBER() OVER (ORDER BY subscription_unit, state, state_subscription, time_based_price_id_val, partner_id, product_id) AS id,
            subscription_unit,
            state,
            state_subscription,
            time_based_price_id_val AS time_based_price_id,
            partner_id,
            company_id,
            product_id,
            product_name,
            plan_name,
            recurrence_name,
            MIN(start_date) AS start_date,
            MAX(next_invoice_date) AS next_invoice_date,
            MAX(end_date) AS end_date,
            MAX(trial_end_date) AS trial_end_date,
            
            -- Counts
            COUNT(DISTINCT subscription_id) AS subscription_count,
            SUM(is_active) AS active_subscription_count,
            SUM(is_trial) AS trial_subscription_count,
            SUM(is_churned) AS churned_subscription_count,
            COUNT(DISTINCT partner_id) AS customer_count,
            COUNT(DISTINCT product_id) AS number_of_product_sold,
            
            -- Revenue Metrics
            SUM(total_price) AS recurring_revenue,
            SUM(CASE WHEN subscription_unit = 'weeks' THEN total_price ELSE 0 END) AS weekly_price_sum,
            SUM(CASE WHEN subscription_unit = 'months' THEN total_price ELSE 0 END) AS monthly_price_sum,
            SUM(CASE WHEN subscription_unit = 'years' THEN total_price ELSE 0 END) AS yearly_price_sum,
            
            -- ARR Calculation (MRR * 12)
            SUM(CASE 
                WHEN subscription_unit = 'months' THEN total_price * 12
                WHEN subscription_unit = 'weeks' THEN total_price * 52
                WHEN subscription_unit = 'years' THEN total_price
                ELSE total_price * 12
            END) AS arr,
            
            -- NRR (for now set to 0, can be enhanced with one-time charges)
            0.0 AS nrr,
            0.0 AS mrr_change,
            0.0 AS arr_change,
            
            -- New subscriptions (created in last 30 days)
            COUNT(DISTINCT CASE 
                WHEN start_date >= NOW() - INTERVAL '30 days' THEN subscription_id 
            END) AS new_subscription_count,
            
            -- New customers (first subscription in last 30 days)
            COUNT(DISTINCT CASE 
                WHEN start_date >= NOW() - INTERVAL '30 days' THEN partner_id 
            END) AS new_customer_count,
            
            -- Churned customers (churned in last 30 days)
            COUNT(DISTINCT CASE 
                WHEN state_subscription = 'churned' THEN partner_id 
            END) AS churned_customer_count,
            
            -- Performance Metrics (calculated correctly at aggregate level)
            CASE 
                WHEN COUNT(DISTINCT subscription_id) > 0 THEN 
                    ROUND((SUM(is_churned)::numeric / COUNT(DISTINCT subscription_id)::numeric * 100), 2)
                ELSE 0 
            END AS churn_rate,
            
            CASE 
                WHEN COUNT(DISTINCT subscription_id) > 0 THEN 
                    ROUND((SUM(is_active)::numeric / COUNT(DISTINCT subscription_id)::numeric * 100), 2)
                ELSE 0 
            END AS retention_rate
            
        FROM subscription_data
        GROUP BY 
            subscription_unit, 
            state, 
            state_subscription, 
            time_based_price_id_val,
            partner_id,
            company_id,
            product_id,
            product_name,
            plan_name,
            recurrence_name
        """)
