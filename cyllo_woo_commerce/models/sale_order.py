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


class SaleOrder(models.Model):
    """Class fpr the inherited model sale_order.Contains fields and methods
        related to Woocommerce sale order.
        Methods:
            compute_state_change(self):Method to compute invoiced quantity
                based on the Woocommerce status.
            get_tile_details(self):Method to return the count of instance,
                products, partners and orders to the dashboard.
            get_orders(self):Method to return order details to the dashboard.
            write(self, vals):Supering the write method to update order status
                of the Woocommerce according to the order status in Odoo.
            unlink(self):Supering the unlink function to delete sale order.
            sync_orders(self):Method to sync sale orders into Woocommerce."""
    _inherit = 'sale.order'

    woo_id = fields.Char(string="WooCommerce ID", copy=False,
                         help='Id in WooCommerce')
    woo_order_key = fields.Char(string="Order Key", readonly=True, copy=False,
                                help='Woo Commerce Order key')
    instance_id = fields.Many2one('woo.commerce.instance', string="Instance",
                                  readonly=True, copy=False,
                                  help='WooCommerce Instance id.')
    woo_order_status = fields.Selection(
        [('pending_payment', 'Pending Payment'), ('processing', 'Processing'),
         ('on_hold', 'On Hold'), ('completed', 'Completed'),
         ('cancelled', 'Cancelled'), ('refunded', 'Refunded'),
         ('failed', 'Failed'), ('draft', 'Draft')], default='draft',
        string='Woo Commerce Status', help='State of order in Woo commerce.')
    state_check = fields.Boolean(compute='compute_state_change',
                                 help='Field to check the state of the order')


    def compute_state_change(self):
        """Method to compute invoiced quantity based on the
            Woocommerce status."""
        if self.woo_order_status != 'completed':
            for order in self.order_line:
                order.qty_invoiced = 0
        self.state_check = True

    @api.model
    def get_tile_details(self):
        """Method to return the count of instance, products, partners
            and orders to the dashboard.
            :return: Returns dictionary with the count of instance, products,
                partners and orders."""
        return {
            'instance': self.env['woo.commerce.instance'].search_count([]),
            'products': self.env['product.template'].search_count(
                [('woo_id', '!=', False)]),
            'partners': self.env['res.partner'].search_count(
                [('woo_id', '!=', False)]),
            'orders': self.env['sale.order'].search_count(
                [('woo_id', '!=', False)]),
        }

    @api.model
    def get_orders(self):
        """Method to return order details to the dashboard.
            :return: Returns list of dictionary with order details."""
        orders = self.env['sale.order'].search([('woo_id', '!=', False)])
        orders_list = []
        for order in orders:
            if order.invoice_status == 'no':
                status = 'Nothing to Invoice'
            elif order.invoice_status == 'to invoice':
                status = 'To Invoice'
            elif order.invoice_status == 'invoiced':
                status = 'Fully Invoiced'
            else:
                status = 'Upselling Opportunity'
            orders_list.append({
                'name': order.name,
                'date_order': order.date_order,
                'customer': order.partner_id.name,
                'total': order.amount_total,
                'status': status, })
        return orders_list

    def write(self, vals):
        """Supering the write method to update order status of the Woocommerce
            according to the order status in Odoo.
            :param vals: Dictionary with order data.
            :return: Returns record set of sale_order"""
        result = super(SaleOrder, self).write(vals)
        if self.instance_id and self.instance_id.stage_change_orders:
            app = API(
                url="" + self.instance_id.store_url + "/index.php/",
                # Your store URL
                consumer_key=self.instance_id.consumer_key,
                # Your consumer key
                consumer_secret=self.instance_id.consumer_secret,
                # Your consumer secret
                wp_api=True,  # Enable the WP REST API integration
                version="wc/v3",  # WooCommerce WP REST API version
                timeout=500,
            )
            if self.woo_order_status == 'pending_payment':
                status = 'pending'
            elif self.woo_order_status == 'processing':
                status = 'processing'
            elif self.woo_order_status == 'on_hold':
                status = 'on-hold'
            elif self.woo_order_status == 'completed':
                status = 'completed'
            elif self.woo_order_status == 'refunded':
                status = 'refunded'
            elif self.woo_order_status == 'failed':
                status = 'failed'
            elif self.woo_order_status == 'draft':
                status = 'draft'
            elif self.woo_order_status == 'cancelled':
                status = 'cancelled'
            val_list = {
                'status': status
            }
            app.put(f"orders/{self.woo_id}", val_list).json()
        return result

    def unlink(self):
        """Supering the unlink function to delete sale order.
            :return: Returns record set of sale order."""
        for order in self:
            if order.instance_id and order.instance_id.delete_orders:
                app = API(
                    url="" + self.instance_id.store_url + "/index.php/",
                    # Your store URL
                    consumer_key=self.instance_id.consumer_key,
                    # Your consumer key
                    consumer_secret=self.instance_id.consumer_secret,
                    # Your consumer secret
                    wp_api=True,  # Enable the WP REST API integration
                    version="wc/v3",  # WooCommerce WP REST API version
                    timeout=500,
                )
                app.delete(f"orders/{order.woo_id}",
                           params={"force": True}).json()
            return super(SaleOrder, self).unlink()

    def sync_orders(self):
        """Method to sync sale orders into Woocommerce.
            :return: Returns window action of model woo update."""
        return {
            'name': _('Sync Orders'),
            'view_mode': 'form',
            'res_model': 'woo.update',
            'view_id': self.env.ref(
                'cyllo_woo_commerce.woo_update_view_form').id,
            'type': 'ir.actions.act_window',
            'context': {'operation_type': 'orders',
                        'active_ids': self.ids},
            'target': 'new'
        }
