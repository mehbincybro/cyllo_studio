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
import re
import requests
from woocommerce import API
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WooCommerceInstance(models.Model):
    """Class for the model woo_commerce_instance.Contains fields and methods
        of the Woocommerce instance.
    """
    _name = 'woo.commerce.instance'
    _description = "WooCommerce Instance"

    name = fields.Char(string="Instance Name", required=True,
                       help='Name of the Instance')
    color = fields.Integer('Color', help='Color for the Kanban')
    consumer_key = fields.Char(string="Consumer Key", required=True,
                               help='Consumer key of the woocommerce')
    consumer_secret = fields.Char(string="Consumer Secret", required=True,
                                  help='Consumer Secret of the woo commerce.')
    store_url = fields.Char(string="Store URL", required=True,
                            help='Woo commerce store Url')
    currency = fields.Char("Currency", readonly=True, help='Related Currency')
    company_id = fields.Many2one("res.company", help="Company of the Instance",
                                 default=lambda self: self.env.company)
    api_key = fields.Char(string="Api Key", required=True,
                          help='API Key for the instance.')
    state = fields.Selection([('not_connected', 'Not Connected'),
                              ('connected', 'Connected')],
                             default='not_connected',
                             help='State of the instance')
    delete_orders = fields.Boolean(string="Delete Orders",
                                   help="Enabling this option will "
                                        "synchronize the deletion of orders "
                                        "between Cyllo and WooCommerce. When a "
                                        "corresponding order is deleted in "
                                        "Cyllo, the WooCommerce order will "
                                        "also be deleted.")
    stage_change_orders = fields.Boolean(string="State Orders",
                                         help="Enabling this option will "
                                              "synchronize the state of orders "
                                              "between Cyllo and WooCommerce. "
                                              "When a corresponding order  "
                                              "WooCommerce status is changed it"
                                              "will change status of the "
                                              "current order")
    product_delete = fields.Boolean(string="Product Delete",
                                    help="Enabling this option will "
                                         "synchronize the deletion of Products "
                                         "between Cyllo and WooCommerce. When a "
                                         "corresponding product is deleted in "
                                         "Cyllo, the WooCommerce product will "
                                         "also be deleted.")
    customer_delete = fields.Boolean(string="Customer Delete",
                                     help="Enabling this option will "
                                          "synchronize the deletion of Customer"
                                          "between Cyllo and WooCommerce. When a"
                                          "corresponding Customer is deleted in"
                                          "Cyllo, the WooCommerce Customer will "
                                          "also be deleted.")

    @api.onchange('customer_delete')
    def _onchange_customer_delete(self):
        """
        On change method triggered when 'customer_delete' field is modified.

        If 'customer_delete' is enabled, it displays a warning about the
        synchronization of product deletion between Cyllo and WooCommerce.

        """
        if self.customer_delete:
            warning = {
                'title': _('Warning!'),
                'message': _(
                    'Enabling "Delete Customer" will synchronize product '
                    'deletion between Cyllo and WooCommerce. Proceed with '
                    'caution.'),
            }
            return {'warning': warning}

    @api.onchange('product_delete')
    def _onchange_product_delete(self):
        """
        On change method triggered when 'product_delete' field is modified.

        If 'product_delete' is enabled, it displays a warning about the
        synchronization of product deletion between Cyllo and WooCommerce.

        :return: Dictionary containing the warning message.
        """
        if self.product_delete:
            warning = {
                'title': _('Warning!'),
                'message': _(
                    'Enabling "Product Orders" will synchronize product '
                    'deletion between Cyllo and WooCommerce. Proceed with '
                    'caution.'),
            }
            return {'warning': warning}

    @api.onchange('delete_orders')
    def _onchange_delete_orders(self):
        """
        On change method triggered when 'delete_orders' field is modified.

        If 'delete_orders' is enabled, it displays a warning about the
        synchronization of order deletion between Cyllo and WooCommerce.

        :return: Dictionary containing the warning message.
        """
        if self.delete_orders:
            warning = {
                'title': _('Warning!'),
                'message': _(
                    'Enabling "Delete Orders" will synchronize order deletion '
                    'between Cyllo and WooCommerce. Proceed with caution.'),
            }
            return {'warning': warning}

    @api.onchange('stage_change_orders')
    def _onchange_stage_change_orders(self):
        """
         On change method triggered when 'stage_change_orders' field is modified.

         If 'stage_change_orders' is enabled, it displays a warning about the
         synchronization of order stage between Cyllo and WooCommerce.

         :return: Dictionary containing the warning message.
         """
        if self.stage_change_orders:
            warning = {
                'title': _('Warning!'),
                'message': _(
                    'Enabling "Stage Orders" will synchronize the order stage '
                    'between Cyllo and WooCommerce. Any changes in WooCommerce '
                    'order stage will be reflected in Cyllo. Proceed with '
                    'caution.'),
            }
            return {'warning': warning}

    @api.model
    def get_instance_graph(self):
        """Method to return product, customer, order and instance details
            to the dashboard.
            :return: Returns dictionary with dashboard details."""
        instance_records = self.env['woo.commerce.instance'].search([])
        product_count = [self.env['product.template'].search_count(
            [('instance_id', '=', rec.id)]) for rec in instance_records]
        customer_count = [self.env['res.partner'].search_count(
            [('instance_id', '=', rec.id)]) for rec in instance_records]
        order_count = [self.env['sale.order'].search_count(
            [('instance_id', '=', rec.id)]) for rec in instance_records]
        instance_name = [rec.name for rec in instance_records]
        return {
            'instance_name': instance_name,
            'product_len': product_count,
            'customer_len': customer_count,
            'order_len': order_count
        }

    def get_api(self):
        """Returns API object.
            :return: Returns binary object."""
        woo_api = API(
            url="" + self.store_url + "/index.php/",  # Your store URL
            consumer_key=self.consumer_key,  # Your consumer key
            consumer_secret=self.consumer_secret,  # Your consumer secret
            wp_api=True,  # Enable the WP REST API integration
            version="wc/v3",  # WooCommerce WP REST API version
            timeout=500,
        )
        return woo_api

    def get_wizard(self):
        """Function used for returning wizard view for operations.
            :return: Returns window action of woo_operation model."""
        set_woo_api = API(
            url=self.store_url + "/index.php/wp-json/wc/v3/system_status?",
            consumer_key=self.consumer_key,  # Your consumer key
            consumer_secret=self.consumer_secret,  # Your consumer secret
            wp_api=True,  # Enable the WP REST API integration
            version="wc/v3",  # WooCommerce WP REST API version
            timeout=500
        )
        set_res = set_woo_api.get("").json()
        self.currency = set_res['settings'].get('currency')
        return {
            'name': _('Instance Operations'),
            'view_mode': 'form',
            'res_model': 'woo.operation',
            'domain': [],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_name': self.name,
                        'default_consumer_key': self.consumer_key,
                        'default_consumer_secret': self.consumer_secret,
                        'default_store_url': self.store_url,
                        'default_api_key': self.api_key,
                        'default_currency': self.currency,
                        'default_company': self.company_id
                        }
        }

    def get_instance(self):
        """Method for returning current form view of instance.
           :return: Returns window action of woo_commerce_instance model."""
        return {
            'name': _('Instance'),
            'view_mode': 'form',
            'res_model': 'woo.commerce.instance',
            'res_id': self.id,
            'domain': [],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Supering the create function to checks all the connection
            validations.
            :param vals_list: Dictionary of record values.
            :return: Returns record set of WooCommerceInstance."""
        attachment_id = self.env['ir.attachment'].sudo().search(
            domain=[('res_model', '=', 'product.template'),
                    ('res_field', '=', 'image_1920')])
        if attachment_id:
            attachment_id.public = True
        for item in vals_list:
            site_url = item['store_url']
            set_woo_api = API(
                url=f"{site_url}/index.php/wp-json/wc/v3/system_status?",
                consumer_key=item['consumer_key'],
                consumer_secret=item['consumer_secret'],
                wp_api=True,  # Enable the WP REST API integration
                version="wc/v3",  # WooCommerce WP REST API version
                timeout=500,
            )
            regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            url_status = re.match(regex, set_woo_api.url) is not None
            if not url_status:
                raise UserError(_("URL Doesn't Exist."))
            try:
                requests.get(set_woo_api.url)
            except requests.ConnectionError as exception:
                raise UserError(_("URL Doesn't Exist."))
            if set_woo_api.get("").status_code != 200:
                raise UserError(_("URL Doesn't Exist or Authentication"
                                  " Issue."))
            set_res = set_woo_api.get("").json()
            if set_res['settings']:
                item['currency'] = set_res['settings'].get('currency')
                if item['currency']:
                    item['state'] = 'connected'
        return super(WooCommerceInstance, self).create(vals_list)

    def write(self, vals):
        """Supering the write function to prevent the credentials changing.
            :param vals: Dictionary of record values.
            :return: Returns the record set of WooCommerceInstance."""
        attachment_id = self.env['ir.attachment'].sudo().search(
            domain=[('res_model', '=', 'product.template'),
                    ('res_field', '=', 'image_1920')])
        if attachment_id:
            attachment_id.public = True
        keys = ['store_url', 'consumer_key', 'consumer_secret']
        for key in keys:
            if key in vals.keys():
                raise UserError(_("You Can't Change Credential Details Ones "
                                  "it was created."))
        return super(WooCommerceInstance, self).write(vals)

    def sync_cron(self):
        """Method of scheduled action that call another function to syncs
            Woocommerce data."""
        woo_operation = self.env['woo.operation'].search([])
        if woo_operation:
            woo_operation[0].sync_details()
