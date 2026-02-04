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
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1.0,
                              parent_combination=False, **kwargs):
        # Call super to get the context, currency, and tax objects
        res = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty,
            parent_combination=parent_combination)

        # Identify the Subscription Plan
        plan_id = kwargs.get('plan_id')
        if not plan_id and self.is_subscription and self.time_based_ids:
            plan_id = self.time_based_ids[:1].id

        if plan_id and str(plan_id).isdigit():
            plan = self.env['time.based.price'].sudo().browse(int(plan_id))
            if plan.exists():
                # Handle Currency Conversion
                # Convert plan cost to the currency currently used by the website
                website_currency = res.get('currency') or self.env.company.currency_id
                website = self.env['website'].get_current_website().with_context(self.env.context)
                pricelist = website.pricelist_id
                if pricelist and pricelist.currency_id == website_currency:
                    time_based_price_rule = pricelist._get_time_based_price_rule(self.id,plan.subscription_unit,plan.duration,fields.Datetime.now(),add_qty)
                if time_based_price_rule:
                       price = time_based_price_rule.fixed_price
                else:
                     price = plan.currency_id._convert(plan.cost,website_currency,self.env.company,self.env.context.get('date') or fields.Date.today())
                # Apply Taxes manually
                # We use the taxes already calculated by super() in res['product_taxes']
                # and res['taxes'] (which handles fiscal positions).
                if res.get('taxes'):
                    price = self._apply_taxes_to_price(
                        price,
                        website_currency,
                        res['product_taxes'],
                        res['taxes'],
                        self.env['product.product'].browse(res['product_id']) or self
                    )

                #  Update the response
                # Now 'price' and 'list_price' contain the tax-adjusted values
                res.update({
                    'price': price,
                    'list_price': price,
                })

        return res
#
