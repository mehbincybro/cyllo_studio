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
from woocommerce import API
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    """Class for the inherited model product_template. Contains fields and
        methods related to Woocommerce product.
        Methods:
            unlink(self):Supering unlink function for deleting values on all
                instances.
            get_product_graph(self):Method to get product details for product
                graph.
            image_upload(self, product):Method to Upload product image into
                WordPress media to get a public link.
            sync_products(self):Method to sync products into Woocommerce."""
    _inherit = 'product.template'
    _description = "Product Template"

    woo_id = fields.Char(string="WooCommerce ID", readonly=True, copy=False,
                         help='Id in WooCommerce')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
    woo_variant_check = fields.Boolean(readonly=True, copy=False,
                                       help='Field to check if the product is '
                                            'variant or not.')

    def unlink(self):
        """Supering unlink function for deleting values on all instances.
           :return: Record set of ProductTemplate."""
        for product in self:
            if product.woo_id and product.instance_id and product.instance_id.product_delete:
                woo_api = product.instance_id.get_api()
                woo_api.delete("products/" + product.woo_id + "",
                               params={"force": True}).json()
        return super(ProductTemplate, self).unlink()

    @api.model
    def get_product_graph(self):
        """Method to get product details for product graph.
            :return: Returns list of dictionary with product details."""
        woo_products = self.env['product.template'].search(
            [('woo_id', '!=', False)])
        products_details = [{'id': product.id, 'name': product.name,
                             'quantity': product.qty_available,
                             'price': product.list_price} for product in
                            woo_products]
        return products_details

    def image_upload(self, product):
        """Method to Upload product image into WordPress media to get a public
             link.
            :param product: Record set of product.
            :return: Returns product image url."""
        attachment_id = self.env['ir.attachment'].sudo().search(
            [('res_model', '=', 'product.template'),
             ('res_id', '=', product.id), ('res_field', '=', 'image_1920')])
        product_image_url = False
        if attachment_id:
            attachment_id.public = True
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url')
            product_image_url = f"{base_url}{attachment_id.image_src}.png"
        return product_image_url

    def sync_products(self):
        """Method to sync products into Woocommerce.
            :return: Returns window action of model woo_update."""
        for product_id in self:
            if product_id.instance_id:
                app = API(
                    url="" + product_id.instance_id.store_url + "/index.php/",
                    # Your store URL
                    consumer_key=product_id.instance_id.consumer_key,
                    # Your consumer key
                    consumer_secret=product_id.instance_id.consumer_secret,
                    # Your consumer secret
                    wp_api=True,  # Enable the WP REST API integration
                    version="wc/v3",  # WooCommerce WP REST API version
                    timeout=500,
                )
                image_url = self.image_upload(product_id)
                val_list = {
                    "name": product_id.name,
                    "regular_price": str(product_id.list_price),
                    "description": product_id.description if product_id.description else "",
                    "sku": product_id.default_code if product_id.default_code else "",
                    'manage_stock': True if product_id.detailed_type == 'product' else False,
                    'stock_quantity': str(product_id.qty_available),
                    "images": [
                        {
                            "src": image_url,
                        }
                    ],
                }
                categories = [{
                    'id': product_id.categ_id.woo_id,
                    'name': product_id.categ_id.name,
                    'slug': product_id.categ_id.name
                }]
                val_list.update({
                    "categories": categories
                })
                app.put(f"products/{product_id.woo_id}", val_list).json()
        return {
            'name': _('Sync Products'),
            'view_mode': 'form',
            'res_model': 'woo.update',
            'view_id': self.env.ref(
                'cyllo_woo_commerce.woo_update_view_form').id,
            'type': 'ir.actions.act_window',
            'context': {'operation_type': 'products', 'active_ids': self.ids},
            'target': 'new'
        }
