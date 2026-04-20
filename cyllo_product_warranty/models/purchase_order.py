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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    display_extend_warranty = fields.Boolean(compute='_compute_display_extend_warranty')

    def _compute_display_extend_warranty(self):
        is_extend_warranty = self.env['ir.config_parameter'].sudo().get_param('cyllo_product_warranty.is_extend_warranty_purchase')
        for order in self:
            order.display_extend_warranty = is_extend_warranty

    def action_extend_warranty(self):
        self.ensure_one()
        has_warranty = any(line.product_id._get_warranty_definition()[0] > 0 for line in self.order_line)
        if not has_warranty:
            raise UserError(_("This Purchase Order does not contain any products with a valid warranty to extend."))
        return {
            'name': 'Extend Warranty',
            'type': 'ir.actions.act_window',
            'res_model': 'warranty.extension.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_order_id': self.id,
            }
        }
