# -*- coding: utf-8 -*-
from odoo import fields, models


class StockQuant(models.Model):
    """
    In the class StockQuant adding some field in the model 'stock.quant'.
    """
    _inherit = 'stock.quant'

    created_cyllo_barcode = fields.Boolean(default=False)
