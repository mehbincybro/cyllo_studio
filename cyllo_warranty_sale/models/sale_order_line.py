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
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warranty_expiration_date = fields.Date(
        string="Warranty Expiration Date",
        compute='_compute_warranty_expiration_date',
        store=True,
    )
    warranty_extension_period = fields.Integer(
        string="Warranty Extension Period",
        default=0,
    )
    warranty_extension_unit = fields.Selection(
        selection=[
            ('day', 'Days'),
            ('month', 'Months'),
            ('year', 'Years'),
        ],
        string="Warranty Extension Unit",
        default='month',
    )
    is_under_warranty = fields.Boolean(
        string="Is Under Warranty",
        compute='_compute_is_under_warranty',
        search='_search_is_under_warranty',
    )

    @api.depends(
        'state',
        'order_id.date_order',
        'product_id',
        'product_id.product_tmpl_id.warranty_period',
        'product_id.product_tmpl_id.warranty_period_unit',
        'product_id.product_tmpl_id.categ_id.warranty_period',
        'product_id.product_tmpl_id.categ_id.warranty_period_unit',
        'warranty_extension_period',
        'warranty_extension_unit',
    )
    def _compute_warranty_expiration_date(self):
        for line in self:
            if not line.order_id.date_order or not line.product_id:
                line.warranty_expiration_date = False
                continue
            expiration_date = line.product_id._get_warranty_expiration_date(
                line.order_id.date_order
            )
            if expiration_date and line.warranty_extension_period > 0:
                if line.warranty_extension_unit == 'day':
                    expiration_date += relativedelta(days=line.warranty_extension_period)
                elif line.warranty_extension_unit == 'year':
                    expiration_date += relativedelta(years=line.warranty_extension_period)
                else:
                    expiration_date += relativedelta(months=line.warranty_extension_period)
            line.warranty_expiration_date = expiration_date

    @api.depends('warranty_expiration_date')
    def _compute_is_under_warranty(self):
        today = fields.Date.context_today(self)
        for line in self:
            line.is_under_warranty = (
                line.warranty_expiration_date and
                line.warranty_expiration_date >= today
            )

    def _search_is_under_warranty(self, operator, value):
        today = fields.Date.context_today(self)
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('warranty_expiration_date', '>=', today)]
        return [('warranty_expiration_date', '<', today)]
