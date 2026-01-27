# -*- coding: utf-8 -*-
from odoo import fields, models


class StockReturnPicking(models.TransientModel):
    """Interface for stock return pickling"""
    _inherit = 'stock.return.picking'

    picking_ids = fields.Many2many('stock.picking')
