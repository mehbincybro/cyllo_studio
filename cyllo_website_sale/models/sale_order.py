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
from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        """ Find the cart line matching the product AND the selected plan """
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)

        # If we are looking for a specific plan from the website
        plan_id = kwargs.get('time_based_price_id')

        if plan_id:
            # Filter the lines to find one that has the SAME plan
            lines = lines.filtered(lambda l: l.time_based_price_id.id == int(plan_id))
        elif not line_id:
            # If no plan is passed, only match lines that HAVE NO plan
            lines = lines.filtered(lambda l: not l.time_based_price_id)

        return lines