# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderTemplateLine(models.Model):
    """Add fields to the model"""
    _inherit = 'sale.order.template.line'

    product_template_id = fields.Many2one(related='product_id.product_tmpl_id', help='Product template')
