# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMove(models.Model):
    """
    StockMove class is used to assigning serial number to the received products
    """
    _inherit = 'stock.move'

    done_quantity = fields.Integer(string="Done Quantity in Barcode", copy=False, compute="_compute_done_quantity",
                                   inverse="_inverse_done_quantity")
    with_barcode = fields.Boolean(default=False, copy=False)

    def _compute_done_quantity(self):
        """Set 'done_quantity' to 'quantity' if 'with_barcode' is True, else set it to 0."""
        for move in self:
            move.done_quantity = move.quantity if move.with_barcode else 0

    def _inverse_done_quantity(self):
        """Set 'quantity' to 'done_quantity' for each record in the collection."""
        for move in self:
            move.quantity = move.done_quantity

    def generate_serial_numbers(self, kwargs):
        """
        Action for assigning serial number to the received products
        """
        self.next_serial = kwargs.get('sn')
        return self._generate_serial_numbers(self.next_serial, next_serial_count=int(kwargs.get('count')))


class StockMoveLine(models.Model):
    """
        StockMoveLine class is used to add field lot_serial_name
    """
    _inherit = 'stock.move.line'

    lot_serial_name = fields.Char(string='Scanned Lot Serial')
