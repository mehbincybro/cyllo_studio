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


class ProductAttribute(models.Model):
    """
    Class for the inherited model product_attribute. Contains fields
    related to Woocommerce attributes.
    """
    _inherit = 'product.attribute'

    woo_id = fields.Char(string="WooCommerce ID", readonly=True, copy=False,
                         help='Id in WooCommerce')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
    slug = fields.Char(string='Slug', help='Slug value of the attribute.')

    _sql_constraints = [
        ('unique_slug', 'UNIQUE(slug)', 'The slug must be unique'),
    ]


class ProductAttributeValue(models.Model):
    """
    Class for the inherited model product_attribute_value. Contains fields
    related to Woocommerce attribute values.
    """
    _inherit = "product.attribute.value"

    woo_id = fields.Char(string="WooCommerce ID", readonly=True, copy=False,
                         help='Id in WooCommerce')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
    slug = fields.Char(string='Slug', help='Slug value of the attribute.')

    _sql_constraints = [
        ('unique_slug', 'UNIQUE(slug)', 'The slug must be unique')]
