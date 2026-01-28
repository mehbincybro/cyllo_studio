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
from odoo import http
from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleSubscription(WebsiteSale):

    @route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, **kw):

        res = super().cart_update_json(
            product_id, line_id, add_qty, set_qty, **kw
        )

        order = request.website.sale_get_order()

        if res.get('line_id'):
            sol_line = order.order_line.browse(res['line_id'])

            plan_id = kw.get('time_based_price_id') or sol_line.time_based_price_id
            if plan_id and sol_line.exists():
                plan = request.env['time.based.price'].sudo().browse(int(plan_id))

                sol_line.write({
                    'time_based_price_id': plan.id,
                    'end_date': kw.get('end_date'),
                })

                sol_line._onchange_time_based_price_id()
                sol_line._compute_price_unit()
                sol_line._compute_amount()

                currency = order.pricelist_id.currency_id
                show_tax = (
                    order.website_id.show_line_subtotals_tax_selection == 'tax_included'
                )

                if 'notification_info' in res:
                    for notify_line in res['notification_info'].get('lines', []):
                        if notify_line.get('id') == sol_line.id:
                            notify_line.update({
                                'price_unit': sol_line.price_unit,
                                'line_price_total': (
                                    sol_line.price_total
                                    if show_tax else sol_line.price_subtotal
                                ),
                                'currency_id': currency.id,
                                'display_price': sol_line.price_unit,
                                'name': f"{sol_line.product_id.name} ({plan.name})",
                            })
                    res['notification_info'].setdefault(
                        'cart_quantity',
                        order.cart_quantity
                    )

        return res

class CustomWebsiteSale(WebsiteSaleVariantController):

    @route('/website_sale/get_combination_info', type='json', auth='public', methods=['POST'], website=True)
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty,
                                     parent_combination=None, **kwargs):
        # Use the class name explicitly in super if super() fails
        res = super().get_combination_info_website(
            product_template_id, product_id, combination, add_qty, parent_combination, **kwargs
        )

        # Now perform your logic to inject **kwargs into the model call
        product_template = request.env['product.template'].sudo().browse(int(product_template_id))

        # We re-run the model method because the base controller
        # ignores the **kwargs you sent from JS
        combination_info = product_template._get_combination_info(
            combination=request.env['product.template.attribute.value'].sudo().browse(combination),
            product_id=product_id and int(product_id),
            add_qty=add_qty and float(add_qty) or 1.0,
            parent_combination=request.env['product.template.attribute.value'].sudo().browse(parent_combination),
            **kwargs
        )

        res.update(combination_info)
        return res


class WebsiteSaleCartCheck(http.Controller):

    @http.route(['/shop/cart/get_info_json'], type='json', auth="public", website=True)
    def get_cart_info_json(self):
        order = request.website.sale_get_order()
        if not order:
            return {'has_subscription': False, 'has_normal': False}

        # Check for presence of different product types
        lines = order.order_line.filtered(lambda l: not l.is_delivery)
        has_sub = any(l.product_id.is_subscription for l in lines)
        has_normal = any(not l.product_id.is_subscription for l in lines)

        return {
            'has_subscription': has_sub,
            'has_normal': has_normal
        }