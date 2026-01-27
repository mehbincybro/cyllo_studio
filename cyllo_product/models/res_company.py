# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Adding fields for approval actions"""
    _inherit = 'res.company'

    product_approver_ids = fields.Many2many(comodel_name='res.users', string='Product Approval Managers',
                                            relation="product_approver_rel",
                                            domain=lambda self: [("groups_id", "=", self.env.ref(
                                                "cyllo_product.group_cyllo_product").id)],
                                            help='List of approvers')
    product_approval_type = fields.Selection(selection=[
        ('single_level', 'Single Level'), ('multi_level', 'Multi Level')])
    price_limit = fields.Float(help='Set the price Limit for the product')
    category_ids = fields.Many2many('product.category', relation="category_rel",
                                    help='Set which category product need the approval')
    cost_limit = fields.Float(string='Cost Limit Amount', help='Set the cost Limit for the product')
    minimum_price_limit = fields.Boolean(string='Price limit', help='Condition for the price limit')
    minimum_cost_limit = fields.Boolean(string='Cost Limit', help='Condition for the cost limit')
    product_category = fields.Boolean(help='Condition for the category')
