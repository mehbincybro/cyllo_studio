# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssetRepairLine(models.Model):
    """model for asset repair line"""
    _name = 'asset.repair.line'
    _description = 'Account Assets Repair'

    repair_id = fields.Many2one('account.asset.repair', 'Repair')
    repair_action = fields.Selection([('add', 'Add'), ('remove', 'Remove')])
    product_id = fields.Many2one('product.product', required=True)
    product_qty = fields.Float(string="Quantity", default=1)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id')
    unit_price = fields.Float(related='product_id.lst_price')
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal')

    @api.constrains('product_qty')
    def _constrains_unit_price(self):
        for record in self:
            if ((record.product_qty) < 1):
                raise ValidationError("Product minimum quantity is 1")

    @api.depends('product_qty', 'unit_price')
    def _compute_price_subtotal(self):
        """Function for calculating the price_subtotal"""
        for record in self:
            record.price_subtotal = (record.product_qty * record.unit_price)
