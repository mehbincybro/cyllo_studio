# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import fields, models


class AccountMove(models.Model):
    """Inherited the model to add fields and methods"""
    _inherit = 'account.move'

    subscription_order_ids = fields.Many2many('subscription.order',
                                              help='Store ids of the subscription order to sent on cron')
    is_subscription = fields.Boolean(help='Check if the invoice is created from a subscription order')
    renewal_date = fields.Datetime(string='Subscription End', help='Subscription end date')
    trial_period = fields.Char(readonly=True, help='Trial period for the corresponding order')

    def ir_cron_action_post(self):
        """Cron to check the invoice creation method chosen in the subscription
        plan and execute with the conditions"""
        sub_order = self.search([('is_subscription', '=', True), ('state', '=', 'draft')])
        for order in sub_order:
            if order.subscription_order_ids.sale_order_template_id.invoice_creation == 'confirmed':
                order.action_post()
            elif order.subscription_order_ids.sale_order_template_id.invoice_creation == 'sent':
                body = self.env.ref('cyllo_subscription.mail_template_invoice_for_subscription')
                body['email_to'] = order.partner_id.email
                body.sudo().send_mail(order.id, force_send=True)

    def action_post(self):
        """
        Post the accounting move and update subscription renewal dates if
        applicable.
        :return: Result of the super method `action_post`
        :rtype: boolean
        """
        res = super().action_post()
        order = self.env['subscription.order'].search([('name', '=', self.invoice_origin)], limit=1)
        if order and order.subscription_order_line_ids and order.subscription_order_line_ids.time_based_price_id:
            time_based_price = order.subscription_order_line_ids.time_based_price_id
            subscription_unit = time_based_price.subscription_unit
            duration = time_based_price.duration
            if subscription_unit in ('weeks', 'months', 'years'):
                delta = relativedelta(**{subscription_unit: duration})
                order.renewal_date = order.renewal_date + delta
        return res
