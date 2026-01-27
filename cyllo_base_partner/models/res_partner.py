# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    """Inherited model for res.partner with additional fields and methods."""
    _inherit = 'res.partner'

    is_customer = fields.Boolean(
        string="Customer",  help="Enable if it's a customer")
    is_vendor = fields.Boolean(
        string="Vendor", help="Enable if it's a vendor")

    @api.model_create_multi
    def create(self, vals_list):
        """Override the create method to set is_customer and is_vendor
        based on rank values."""
        res = super().create(vals_list)
        for vals in vals_list:
            customer_rank = vals.get('customer_rank', 0)
            supplier_rank = vals.get('supplier_rank', 0)
            if customer_rank and customer_rank > 0:
                res.is_customer = True
            if supplier_rank and supplier_rank > 0:
                res.is_vendor = True
        return res
