from odoo import models, fields


class SubscriptionTrialHistory(models.Model):
    _name = 'subscription.trial.history'
    _description = 'Subscription Trial Usage History'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    subscription_order_id = fields.Many2one('subscription.order', string='Source Subscription')
    date_started = fields.Datetime(string='Trial Start Date', default=fields.Datetime.now)
    date_trial_end = fields.Datetime(string='Trial End Date')

    _sql_constraints = [
        ('unique_trial', 'unique(partner_id, product_id)',
         'This customer has already used a trial for this product!')
    ]