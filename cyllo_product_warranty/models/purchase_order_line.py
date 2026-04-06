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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    warranty_expiration_date = fields.Date(
        string="Warranty Expiration Date",
        compute='_compute_warranty_expiration_date',
        store=True,
    )

    @api.depends(
        'state',
        'order_id.date_approve',
        'product_id',
        'product_id.product_tmpl_id.warranty_period',
        'product_id.product_tmpl_id.warranty_period_unit',
        'product_id.product_tmpl_id.categ_id.warranty_period',
        'product_id.product_tmpl_id.categ_id.warranty_period_unit',
    )
    def _compute_warranty_expiration_date(self):
        for line in self:
            date = line.order_id.date_approve or line.order_id.date_order
            if not date or not line.product_id:
                line.warranty_expiration_date = False
                continue
            line.warranty_expiration_date = line.product_id._get_warranty_expiration_date(
                date
            )
