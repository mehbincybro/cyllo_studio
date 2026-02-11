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
from odoo import http,fields
from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo.addons.payment.controllers.portal import PaymentPortal

class WebsiteSaleSubscription(WebsiteSale):
    """Extends the base WebsiteSale controller to handle subscription-specific
        logic in the e-commerce shopping cart and product pages."""

    @route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, **kw):
        """Override to inject subscription plan data into the Sale Order Line
        when updating the cart via AJAX.
        It links the selected 'time_based_price_id' to the line and triggers
        a recomputation of the price based on the selected duration."""

        res = super().cart_update_json(
            product_id, line_id, add_qty, set_qty, **kw
        )

        order = request.website.sale_get_order()

        if res.get('line_id'):
            sol_line = order.order_line.browse(res['line_id'])

            plan_id = kw.get('time_based_price_id') or sol_line.time_based_price_id
            if plan_id and sol_line.exists():
                plan = request.env['time.based.price'].sudo().browse(int(plan_id))

                values = {
                    'time_based_price_id': plan.id,
                    'end_date': kw.get('end_date'),
                }
                
                if kw.get('skip_trial') in [True, 'true', 'True']:
                    values['skip_trial'] = True
                sol_line.write(values)

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
                                'line_price_total': sol_line.price_total if show_tax else sol_line.price_subtotal,
                                'currency_id': currency.id,
                                'display_price': sol_line.price_unit,
                                'name': f"{sol_line.product_id.name} ({plan.name})",
                            })
                    res['notification_info'].setdefault(
                        'cart_quantity',
                        order.cart_quantity
                    )
        order.sudo()._set_trial_discount_line()
        return res

    @http.route('/shop/product/get_sub_pricelist_price', type='json', auth="public", website=True)
    def get_sub_pricelist_price(self, product_temp_id, unit, duration, qty, **kwargs):
        """Fetches the specific subscription price rule from the pricelist for UI updates.
        This is called by JavaScript when a user changes the subscription plan
        dropdown on the product page to show the price before adding to cart."""
        #  Get the current website's active pricelist
        website = request.env['website'].get_current_website().with_context(request.env.context)
        pricelist = website.pricelist_id

        if not pricelist or not product_temp_id:
            return {'price': False}

        # Fallback to plan cost if no rule found, converting currency
        plan = request.env['time.based.price'].sudo().search([
            ('product_template_id', '=', int(product_temp_id)),
            ('subscription_unit', '=', unit),
            ('duration', '=', int(duration))
        ], limit=1)
        
        if plan:
             price = pricelist.sudo()._get_subscription_price(
                 int(product_temp_id),
                 plan,
                 float(qty),
                 fields.Date.today()
             )
             return {'price': price}

        return {'price': False}

    @http.route(['/shop/cart/get_info_json'], type='json', auth="public", website=True)
    def get_cart_info_json(self, product_id=None):
        """Provides metadata about the current cart composition and a specific product.
        Used by the frontend to determine if the cart contains a mix of
        subscription and non-subscription items, which may trigger UI warnings."""
        order = request.website.sale_get_order()
        product = request.env['product.product'].sudo().browse(product_id)
        is_subscription = product.is_subscription if product.exists() else False
        product_has_trial = product.product_tmpl_id.trial_period > 0 if product.exists() else False

        if not order:
            return {
                'is_subscription': False, 
                'has_subscription': False, 
                'has_normal': False,
                'product_has_trial': product_has_trial
            }

        # Check for presence of different product types
        trial_discount_product = request.env.ref('cyllo_website_subscription.product_trial_discount', raise_if_not_found=False)
        lines = order.order_line.filtered(lambda l: not (l.is_delivery or l.product_id == trial_discount_product))
        has_sub = any(l.product_id.is_subscription for l in lines)
        has_normal = any(not l.product_id.is_subscription for l in lines)
        return {
            'is_subscription': is_subscription,
            'has_subscription': has_sub,
            'has_normal': has_normal,
            'product_has_trial': product_has_trial
        }


class CustomWebsiteSale(WebsiteSaleVariantController):
    """Extends the variant controller to handle custom pricing context.
    This class ensures that extra parameters passed from the frontend (time based price id) are correctly passed down to the
    product template's price calculation methods."""
    @route('/website_sale/get_combination_info', type='json', auth='public', methods=['POST'], website=True)
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty,
                                     parent_combination=None, **kwargs):
        """Re-evaluates product combination data to force-inject subscription kwargs,
        ensuring the UI reflects accurate time-based pricing during variant selection."""
        # Use the class name explicitly in super if super() fails
        res = super().get_combination_info_website(
            product_template_id, product_id, combination, add_qty, parent_combination, **kwargs
        )

        product_template = request.env['product.template'].sudo().browse(int(product_template_id))

        combination_info = product_template._get_combination_info(
            combination=request.env['product.template.attribute.value'].sudo().browse(combination),
            product_id=product_id and int(product_id),
            add_qty=add_qty and float(add_qty) or 1.0,
            parent_combination=request.env['product.template.attribute.value'].sudo().browse(parent_combination),
            **kwargs
        )

        res.update(combination_info)
        return res








