# -*- coding: utf-8 -*-
from odoo import models


class StockChangeProductQty(models.TransientModel):
    """Inherits the ProductChangeQuantity class from stock change quantity model."""
    _inherit = "stock.change.product.qty"

    def change_product_qty(self):
        """Function for the change quantity"""
        if self.product_id.is_rental:
            stock_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': self.product_id.id,
                'location_id': self.product_id.rental_location_id.id,
                'inventory_quantity': self.new_quantity})
            stock_quant._apply_inventory()
            return {'type': 'ir.actions.act_window_close'}
        return super().change_product_qty()
