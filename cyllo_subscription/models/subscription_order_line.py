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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SubscriptionOrderLine(models.Model):
    """Model to store order line of subscription order"""
    _name = 'subscription.order.line'
    _description = 'Subscription Order Line'

    product_id = fields.Many2one('product.product',
                                 help='Selected product from order shows here')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id',
                                      string='Product Template',
                                      help='Selected product from order shows here')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line',
                                         help='Sale order line')
    sale_order_id = fields.Many2one('sale.order', help='Sale order reference')
    quantity = fields.Integer(help='Quantity of the products', readonly=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 help='Current company')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Current company currency')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes",
                               help="Choose a tax",
                               context={'active_test': False},
                               domain=[('type_tax_use', '=', 'sale')],
                               check_company=True, readonly=True)
    subtotal = fields.Monetary(help='Subtotal amount')
    total_price = fields.Monetary(help='Total amount')
    subscription_order_id = fields.Many2one('subscription.order',
                                            help='Subscription order reference')
    time_based_price_id = fields.Many2one('time.based.price',
                                          help='Time Based Price',
                                          readonly=True)
    state = fields.Selection(
        related='subscription_order_id.state',
        string="Order Status",
        copy=False, store=True, precompute=True)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Generates user error while removing the lines of the confirmed subscription order"""
        if self._check_line_unlink():
            raise UserError(
                _("Once a subscription order is confirmed, you can't remove one of its lines"))

    def _check_line_unlink(self):
        """ Check whether given lines can be deleted or not.
        """
        return self.filtered(
            lambda line:
            line.state in ('sale', 'posted')
        )