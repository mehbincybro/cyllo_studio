# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """Inherited Sale Order model to add custom functionality for merging quotations."""
    _inherit = 'sale.order'

    def action_merge_quotation(self):
        """Merge selected sale orders with the same partner and in the quotation state.
        Creates a new sale order, consolidates order lines, and deletes the
        original orders. Redirects to the form view of the newly created sale order.
        :return: Action dictionary for redirection.
        :rtype: dict"""
        if len(self) < 2:
            raise ValidationError("Please select at least two orders to merge.")
        reference_partner_id = self[0].partner_id.id
        if any(order.partner_id.id != reference_partner_id for order in self):
            raise ValidationError("Selected orders have different partners.")
        if any(order.state != 'draft' for order in self):
            raise ValidationError("Please select orders in the quotation state.")
        new_sale_order = self.create({"partner_id": reference_partner_id})
        order_lines = {}
        for order in self:
            for line in order.order_line:
                key = (line.product_id.id, line.price_unit)
                if key in order_lines:
                    order_line = order_lines[key]
                    price = order_line.price_unit
                    order_line.product_uom_qty += line.product_uom_qty
                    order_line.price_unit = price
                else:
                    order_lines[key] = line.copy(default={"order_id": new_sale_order.id})
        self.unlink()
        return {
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': new_sale_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
