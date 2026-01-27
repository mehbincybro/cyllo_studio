# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountPayment(models.Model):
    """Inheriting account.payment"""
    _inherit = 'account.payment'

    sale_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    purchase_id = fields.Many2one(comodel_name="purchase.order", string="Purchase Order")
