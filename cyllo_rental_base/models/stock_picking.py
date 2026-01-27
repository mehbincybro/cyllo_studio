# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    """Inherits the stock picking model for adding new field"""
    _inherit = "stock.picking"

    rental_id = fields.Many2one('rental.order')
