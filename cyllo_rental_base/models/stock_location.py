# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLocation(models.Model):
    """Inherits the stock location model for adding new field"""
    _inherit = "stock.location"

    is_rental_location = fields.Boolean(string="Is a Rental Location", help="Enable if this is a rental location")
