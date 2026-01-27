# -*- coding: utf-8 -*-
from odoo import fields, models


class SubscriptionOrderLine(models.Model):
    """Model to store order line of subscription order"""
    _name = 'subscription.order.line'
    _description = 'Subscription Order Line'

    product_id = fields.Many2one('product.product', help='Selected product from order shows here')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', string='Product Template',
                                      help='Selected product from order shows here')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line', help='Sale order line')
    sale_order_id = fields.Many2one('sale.order', help='Sale order reference')
    quantity = fields.Integer(help='Quantity of the products', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, help='Current company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', help='Current company currency')
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", help="Choose a tax",
                               context={'active_test': False}, domain=[('type_tax_use', '=', 'sale')],
                               check_company=True, readonly=True)
    subtotal = fields.Monetary(help='Subtotal amount')
    total_price = fields.Monetary(help='Total amount')
    subscription_order_id = fields.Many2one('subscription.order', help='Subscription order reference')
    time_based_price_id = fields.Many2one('time.based.price', help='Time Based Price', readonly=True)
