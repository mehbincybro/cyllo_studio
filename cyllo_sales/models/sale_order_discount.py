# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderDiscount(models.TransientModel):
    """Inherited Sale Order discount model to add custom functionality forDiscount """
    _inherit = 'sale.order.discount'

    apply_order_lines = fields.Boolean(string="Apply To OrderLines?",
                                       help="Allows to apply the discount on current order lines")

    def _create_discount_lines(self):
        """ Super the function to apply global discount in orderLines """
        if self.apply_order_lines:
            if self.discount_type == 'so_discount':
                discount_in_percentage = self.discount_percentage * 100
            else:
                if self.sale_order_id.amount_total > 0 and self.discount_amount > 0:
                    discount_in_percentage = self.discount_amount * 100 / self.sale_order_id.amount_total
                else:
                    discount_in_percentage = 0
            for line in self.sale_order_id.order_line:
                line.discount += discount_in_percentage
        else:
            return super()._create_discount_lines()
