# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_subscription = fields.Boolean(string='Is Subscription', readonly=True)
