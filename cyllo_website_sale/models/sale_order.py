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

    def _set_trial_discount_line(self):
        """Adds or updates a trial discount line to offset subscription costs."""
        self.ensure_one()
        trial_product = self.env.ref('cyllo_website_sale.product_trial_discount', raise_if_not_found=False)
        if not trial_product:
            return

        # Sum subtotals of subscription products with a trial period
        trial_sub_lines = self.order_line.filtered(
            lambda l: l.product_id.is_subscription and l.product_template_id.trial_period > 0
        )
        total_to_offset = sum(trial_sub_lines.mapped('price_subtotal'))

        trial_line = self.order_line.filtered(lambda l: l.product_id == trial_product)

        if total_to_offset > 0:
            if trial_line:
                trial_line.sudo().write({
                    'price_unit': -total_to_offset,
                    'product_uom_qty': 1,
                    'tax_id': [(6, 0, trial_sub_lines[0].tax_id.ids)] if trial_sub_lines else []
                })
            else:
                self.env['sale.order.line'].sudo().create({
                    'order_id': self.id,
                    'product_id': trial_product.id,
                    'product_uom_qty': 1,
                    'price_unit': -total_to_offset,
                    'sequence': 999,
                })
        elif trial_line:
            trial_line.sudo().unlink()

    def _compute_amounts(self):
        """Recalculate trial line before final totals."""
        for order in self:
            if order.website_id:
                order._set_trial_discount_line()
        return super()._compute_amounts()

    def _get_subscription_trial_offset(self):
        """Calculates total value of trial items for display masking."""
        price_total =sum(self.order_line.filtered(
            lambda l: l.product_id.is_subscription and l.product_template_id.trial_period > 0
        ).mapped('price_total'))
        price_subtotal = sum(self.order_line.filtered(
            lambda l: l.product_id.is_subscription and l.product_template_id.trial_period > 0
        ).mapped('price_subtotal'))
        tax_total = sum(self.order_line.filtered(
            lambda l: l.product_id.is_subscription and l.product_template_id.trial_period > 0
        ).mapped('price_tax'))
        return price_total,tax_total, price_subtotal