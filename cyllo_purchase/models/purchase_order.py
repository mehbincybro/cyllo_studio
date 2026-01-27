# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    """
        Inherited Purchase Order model to add custom functionality for merging
        RFQ.
    """
    _inherit = 'purchase.order'
    is_global_discount = fields.Boolean(string='Global Discount',
                                        help="If enabled it allows to add global discount for the purchase order")
    discount_type = fields.Selection(string='Discount types', help="Choose the discount type",
                                     selection=[('amount', 'Amount'), ('percentage', 'Percentage')])
    discount_amount = fields.Float(string="Discount in Amount", help="Enter the discount rate")
    discount_percentage = fields.Float(string="Discount in Percentage", help="Enter the discount percentage")

    def action_merge_rfq(self):
        """
        Merge selected RFQ with the same partner and in the draft state.
        Creates a new RFQ, consolidates order lines, and deletes the original orders.
        Redirects to the form view of the newly created RFQ.
        :return: Action dictionary for redirection.
        :rtype: dict
        """
        if len(self) < 2:
            raise ValidationError("Please select at least two orders to merge.")
        reference_partner_id = self[0].partner_id.id
        if any(order.partner_id.id != reference_partner_id for order in self):
            raise ValidationError("Selected orders have different partners.")
        if any(order.state != 'draft' for order in self):
            raise ValidationError("Please select orders in the RFQ state.")
        new_purchase_order = self.env['purchase.order'].create(
            {"partner_id": reference_partner_id})
        order_lines = {}
        for order in self:
            for line in order.order_line:
                key = (line.product_id.id, line.price_unit)
                if key in order_lines:
                    order_line = order_lines[key]
                    price = order_line.price_unit
                    order_line.product_qty += line.product_qty
                    order_line.price_unit = price
                else:
                    new_line = line.copy(default={"order_id": new_purchase_order.id})
                    order_lines[key] = new_line
        self.sudo().button_cancel()
        self.sudo().unlink()
        return {
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': new_purchase_order.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_apply_discount(self):
        """  function to apply global discount in orderLines """
        if self.discount_type == 'percentage':
            discount_in_percentage = self.discount_percentage
        else:
            if self.discount_amount > 0 and self.amount_total > 0:
                discount_in_percentage = self.discount_amount * 100 / self.amount_total
            else:
                discount_in_percentage = 0
        for line in self.order_line:
            line.discount += discount_in_percentage
