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
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountMove(models.Model):
    """Inherited the model to add fields and methods"""
    _inherit = 'account.move'

    subscription_order_id = fields.Many2one('subscription.order',
                                            help='Store ids of the subscription order to sent on cron')
    is_subscription = fields.Boolean(
        help='Check if the invoice is created from a subscription order')
    renewal_date = fields.Datetime(string='Subscription End',
                                   help='Subscription end date')
    trial_period = fields.Char(readonly=True,
                               help='Trial period for the corresponding order')

    def action_post(self):
        """
        Post the accounting move and update subscription renewal dates if
        applicable.
        :return: Result of the super method `action_post`
        :rtype: boolean
        """
        res = super().action_post()
        order = self.env['subscription.order'].search(
            [('name', '=', self.invoice_origin)], limit=1)
        if order and order.subscription_order_line_ids and order.subscription_order_line_ids.time_based_price_id:
            time_based_price = order.subscription_order_line_ids.time_based_price_id
            subscription_unit = time_based_price.subscription_unit
            duration = time_based_price.duration
            if subscription_unit in ('weeks', 'months', 'years'):
                delta = relativedelta(**{subscription_unit: duration})
                order.renewal_date = order.renewal_date + delta
        return res

    def ir_cron_action_post(self):
        """Cron to check the invoice creation method chosen in the subscription
        plan and execute with the conditions"""
        invoices = self.search(
            [('is_subscription', '=', True), ('state', '=', 'draft')])
        for invoice in invoices:
            if invoice.subscription_order_id.sale_order_template_id.invoice_creation == 'confirmed':
                invoice.action_post()
            elif invoice.subscription_order_id.sale_order_template_id.invoice_creation == 'sent' and invoice.subscription_order_id.sale_order_template_id.subscription_mail_template_id:
                body = invoice.subscription_order_id.sale_order_template_id.subscription_mail_template_id
                body['email_to'] = invoice.partner_id.email
                body.sudo().send_mail(invoice.id, force_send=True)