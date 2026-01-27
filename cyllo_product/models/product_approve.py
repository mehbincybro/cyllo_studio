# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductApprove(models.Model):
    """Model is used add the product form page approve record line"""
    _name = 'product.approve'
    _description = 'Product Approval Lines'

    product_approver_id = fields.Many2one('res.users', string='Approver', help='Product approval user')
    status = fields.Selection(selection=[('pending', 'Pending'), ('approved', 'Approved'),  ('rejected', 'Rejected')],
                              help="The status of each product's request for approval")
    related_product_id = fields.Many2one('product.template', string='Product approve id',
                                         help='Used to connect the product module')
    product_product_id = fields.Many2one('product.product', string='Product', help='Product variant')
    reason = fields.Char(help='Reason for the rejection')
