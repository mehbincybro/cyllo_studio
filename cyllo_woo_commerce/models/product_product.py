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


class ProductProduct(models.Model):
    """Class for the inherited model product_product. Contains fields and
        methods related to Woocommerce products.
    """
    _inherit = 'product.product'

    woo_price = fields.Float(string="woo price", copy=False,
                             help='Price in WooCommerce')
    woo_var_id = fields.Char(string="Woo Variant ID", readonly=True,
                             copy=False, help='Variant Id in WooCommerce.')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Supering create method to update variant values according to
        Woocommerce variant.
        :param vals_list: List of dictionary contains field values.
        :return: Record set of ProductProduct.
        """
        if self._context.get('woocommerce_variant') and self._context.get(
                'variant_vals'):
            for i in vals_list:
                vals_list[i].update(self._context['variant_vals'][i])
        val = super(ProductProduct, self).create(vals_list)
        return val

    def unlink(self):
        """Supering unlink function for deleting values on all instances.
           :return: Record set of ProductProduct."""
        for recd in self:
            if recd.woo_var_id:
                woo_api = recd.product_tmpl_id.instance_id.get_api()
                woo_api.delete(
                    "products/" + recd.product_tmpl_id.woo_id + "/variations/" + recd.woo_var_id + "",
                    params={"force": True}).json()
        return super(ProductProduct, self).unlink()

    @api.depends('list_price', 'price_extra')
    @api.depends_context('uom')
    def _compute_product_lst_price(self):
        """Overriding the compute function of lst_price for changing variant
           price based on the woocommerce price."""
        for recd in self:
            product_id = self.env['product.template'].search(
                [('product_variant_ids', 'in', recd.id)])
            if not product_id.woo_variant_check:
                to_uom = None
                if 'uom' in self._context:
                    to_uom = self.env['uom.uom'].browse(self._context['uom'])
                for product in self:
                    if to_uom:
                        list_price = product.uom_id._compute_price(
                            product.list_price, to_uom)
                    else:
                        list_price = product.list_price
                    product.lst_price = list_price + product.price_extra
            else:
                if recd.woo_price == 0:
                    recd.lst_price = recd.product_tmpl_id.list_price
                else:
                    recd.lst_price = recd.woo_price
