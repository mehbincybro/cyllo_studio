# -*- coding: utf-8 -*-
from odoo import fields, models


class SubscriptionOrderCloseReason(models.Model):
    """Model to store subscription close reasons"""
    _name = "subscription.order.close.reason"
    _description = 'Subscription order close reason'
    _rec_name = 'reason'

    reason = fields.Char(help='Subscription close reason')
    available_in_portal = fields.Boolean(help='If the reason needs to show in portal enable this field')
