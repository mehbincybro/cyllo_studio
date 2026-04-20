# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import fields, models


class WarrantyExtensionWizard(models.TransientModel):
    _name = 'warranty.extension.wizard'
    _description = 'Warranty Extension Wizard'

    order_id = fields.Many2one(
        'sale.order',
        string="Sale Order",
        readonly=True,
    )
    line_ids = fields.Many2many(
        'sale.order.line',
        string="Sale Order Lines",
        domain="[('order_id', '=', order_id), ('is_under_warranty', '=', True)]",
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Purchase Order",
        readonly=True,
    )
    purchase_line_ids = fields.Many2many(
        'purchase.order.line',
        string="Purchase Order Lines",
        domain="[('order_id', '=', purchase_order_id), ('is_under_warranty', '=', True)]",
    )
    extension_period = fields.Integer(
        string="Extension Period",
        required=True,
        default=1,
    )
    extension_unit = fields.Selection(
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('year', 'Years'),
        ],
        string="Extension Unit",
        required=True,
        default='month',
    )

    def action_confirm(self):
        lines = self.line_ids or self.purchase_line_ids
        for line in lines:
            line.write({
                'warranty_extension_period': line.warranty_extension_period + self.extension_period,
                'warranty_extension_unit': self.extension_unit,
            })
        return {'type': 'ir.actions.act_window_close'}
