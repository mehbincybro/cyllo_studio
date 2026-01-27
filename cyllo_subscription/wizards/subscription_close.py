# -*- coding: utf-8 -*-
from odoo import _, fields, models


class SubscriptionClose(models.TransientModel):
    """Transient model to call on subscription close button click"""
    _name = 'subscription.close'
    _description = 'Subscription Close'

    close_reason_id = fields.Many2one('subscription.order.close.reason')
    subscription_order_id = fields.Many2one('subscription.order')

    def action_close(self):
        """Method to close subscription"""
        self.subscription_order_id.state_subscription = 'churned'
        self.subscription_order_id.message_post(
                body=_(f'Subscription order is due to the reason: {self.close_reason_id.reason}'),
                message_type='comment', subtype_xmlid='mail.mt_comment')
