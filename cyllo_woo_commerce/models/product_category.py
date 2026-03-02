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


class ProductCategory(models.Model):
    """Class for the inherited model product_category. Contains fields
        and method related to Woocommerce product categories.
        Methods:
            get_product_category_graph(self):Method to return  product category
            names and count of products into module dashboard."""
    _inherit = 'product.category'

    woo_id = fields.Char(string="WooCommerce ID", copy=False, readonly=True,
                         help='Id in WooCommerce')

    instance_id = fields.Many2one('woo.commerce.instance',
                                  copy=False, readonly=True, string="Instance",
                                  help='Id in WooCommerce')

    @api.model
    def get_product_category_graph(self):
        """Method to return  product category names and count of products into
            module dashboard.
            :return: Returns dictionary of category names and product count.
        """
        categories = self.env['product.category'].search([
            ('woo_id', '!=', False)])
        products_count = [self.env['product.template'].search_count(
            [('categ_id', '=', category.id)]) for category in categories]
        return {
            'categories_name': categories.mapped('name'),
            'products_count': products_count
        }
