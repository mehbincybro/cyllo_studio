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
from itertools import groupby
from operator import itemgetter

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SubscriptionOrder(models.Model):
    """Model Subscription order"""
    _name = "subscription.order"
    _description = 'Subscription Order'
    _inherit = ['mail.thread', 'portal.mixin', 'mail.activity.mixin']

    name = fields.Char(string='Reference Number', copy=False, readonly=True,
                       help='Reference number to identify the order')
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 help='Name of the customer', readonly=True)
    subscription_order_line_ids = fields.One2many('subscription.order.line',
                                                  'subscription_order_id',
                                                  string='Order Line',
                                                  help='Subscription order line')
    sale_order_id = fields.Many2one('sale.order',
                                    help='Corresponding sale order id is saved in the field')
    state_subscription = fields.Selection(
        selection=[('quotation', 'Quotation'), ('active', 'Active'),
                   ('renew', 'Renew'), ('churned', 'Churned'),
                   ('trial', 'On Trial')], default='active',
        string='Subscription State',
        help='State of the subscription order shows here')
    renewal_date = fields.Datetime(string='Next Invoice Date',
                                   help='Date to renew the subscription')
    sale_order_template_id = fields.Many2one('sale.order.template',
                                             string='Subscription Plan',
                                             help='Plan chosen in order shows here')
    time_based_price_id = fields.Many2one('time.based.price',
                                          string='Recurrence', required=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count',
                                   help='Count of the invoice')
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('sale', 'Sale'), ('posted', 'Posted'),('requested', 'Requested'),],
        default='draft',
        help='State of the order')
    recurring_revenue = fields.Float(string='MRR',
                                     help='Monthly recurring revenue',
                                     compute='_compute_recurring_revenue',
                                     store=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 help='Current logged in company shows here')
    trial_end = fields.Datetime(string='Trial End Date',
                                help='Trial period ending date')
    partner_street = fields.Char(compute='_compute_partner_street', store=True,
                                 help='Main street of partner shows here')
    partner_city = fields.Char(related='partner_id.city', string='City')
    partner_state = fields.Char(related='partner_id.state_id.name')
    check_upsell_renewal = fields.Boolean(string='Check Upsell/Renewal',
                                          help='Check if the button clicked is renewal or upsell')
    account_move_ids = fields.Many2many('account.move', string='Invoices',
                                        help='Invoice records store here')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Current company currency')
    amount_untaxed = fields.Monetary(string='Untaxed Amount',
                                     compute='_compute_amounts')
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts')
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts')
    parent_id = fields.Many2one(string='Parent Subscription Order',
                                comodel_name='subscription.order')
    end_date = fields.Datetime(string='End Date')

    def _compute_invoice_count(self):
        """Compute invoice count"""
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count(
                [('invoice_origin', '=', rec.name)])

    @api.depends('state_subscription', 'state')
    def _compute_recurring_revenue(self):
        """Methode to compute recurring revenue"""
        for revenue in self:
            revenue.recurring_revenue = revenue.subscription_order_line_ids.subtotal

    def _compute_partner_street(self):
        """
        Compute the complete street address for each record.
        :return: None
        """
        for rec in self:
            street = rec.partner_id.street if rec.partner_id.street else ''
            street2 = rec.partner_id.street2 if rec.partner_id.street2 else ''
            rec.partner_street = f'{street} {street2}'

    @api.depends('subscription_order_line_ids.subtotal',
                 'subscription_order_line_ids.total_price')
    def _compute_amounts(self):
        """function for amount computation"""
        for order in self:
            amount_untaxed = sum(
                line.subtotal for line in order.subscription_order_line_ids)
            amount_total = sum(
                line.total_price for line in order.subscription_order_line_ids)
            amount_tax = amount_total - amount_untaxed
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

    def _compute_access_url(self):
        """Access url computation"""
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/details/{request.id}'

    @api.model_create_multi
    def create(self, vals):
        """Sequence number for subscription order"""
        for rec in vals:
            if rec.get('name', _('New')) == _('New'):
                rec['name'] = self.env['ir.sequence'].next_by_code(
                    'subscription.order') or 'New'
        return super().create(vals)

    def unlink(self):
        """If the state of subscription order is in sale or posted state then it cannot be unlinked"""
        if self.state in ['sale', 'posted']:
            raise ValidationError(
                _("You cannot delete order in Sale or Posted state"))
        return super().unlink()

    def action_post(self):
        """Create invoice for subscription"""
        if self.end_date and self.renewal_date and self.end_date < self.renewal_date:
            raise ValidationError(_("The requested billing period exceeds the current subscription duration."))
        if self.env['account.move'].search_count(
                [('invoice_origin', '=', self.name),
                 ('state', '=', 'draft')]) >= 1:
            raise ValidationError(
                _('There is already a draft invoice is present for this order, so please confirm it '
                  'or cancel it before proceed.'))
        inv = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'payment_reference': self.name,
            'invoice_origin': self.name,
            'invoice_date_due': self.renewal_date,
            'renewal_date': self.renewal_date,
            'date': fields.Datetime.now(),
            'is_subscription': True,
            'subscription_order_id': self.id,
            'trial_period': f'{self.subscription_order_line_ids.product_id.trial_period} '
                            f'{self.subscription_order_line_ids.product_id.unit}',
            'invoice_line_ids': [fields.Command.create({
                'product_id': self.subscription_order_line_ids.product_id.id,
                'price_unit': 0 if self.subscription_order_line_ids.product_id.trial_period > 0 else
                self.subscription_order_line_ids.subtotal
            })],
        })
        self.state = 'posted'
        if self.sale_order_template_id.invoice_creation == 'confirmed':
            inv.action_post()
        elif self.sale_order_template_id.invoice_creation == 'sent':
            inv.action_post()
            body = self.sale_order_template_id.subscription_mail_template_id
            body['email_to'] = self.partner_id.email
            body.sudo().send_mail(inv.id, force_send=True)
        self.account_move_ids = inv.ids
        return {
            'name': 'Invoice',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_id': inv.id
        }

    def action_show_invoices(self):
        """Display the invoices created from a particular order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', self.env['account.move'].search(
                [('invoice_origin', '=', self.name)]).ids)]
        }

    def action_view_report(self):
        """View reporting"""
        return self.env["ir.actions.actions"]._for_xml_id(
            "cyllo_subscription.action_view_reporting")

    def action_renew_order(self):
        """Renew the contract"""
        if self.state == "posted":
            subscription_ids = self.env['subscription.order'].search(
                [('parent_id','=',self.id)])
            for subscription in subscription_ids:
                if(subscription.state_subscription == 'active'):
                    raise ValidationError("You already have an active subscription for this order.")
            self.check_upsell_renewal = True
            return self.action_sub_renew_upsell()
        else:
            raise ValidationError("Order must be in 'posted' state to renew.")

    def action_upsell(self):
        """Upsell the contract"""
        self.check_upsell_renewal = False
        return self.action_sub_renew_upsell()

    def action_sub_renew_upsell(self):
        """Method is used when creation of upsell or renewal"""
        if self.invoice_count <= 0:
            raise ValidationError(
                _("Upsell or renewal isn’t allowed for subscriptions without an invoice. "
                  "Kindly invoice the %s contract first or modify it directly.",
                  self.name))
        order = self.create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'renewal_date': self.renewal_date,
            'parent_id':self.id,
            'sale_order_template_id': self.sale_order_template_id.id,
            'time_based_price_id': self.time_based_price_id.id,
            'sale_order_id': self.sale_order_id.id,
            'trial_end': False,
            'subscription_order_line_ids': [
                (fields.Command.create({
                    'product_id': self.subscription_order_line_ids.product_id.id,
                    'product_tmpl_id': self.subscription_order_line_ids.product_tmpl_id,
                    'quantity': self.subscription_order_line_ids.quantity,
                    'time_based_price_id': self.time_based_price_id.id,
                    'subtotal': self.subscription_order_line_ids.subtotal,
                    'tax_ids': self.subscription_order_line_ids.tax_ids.ids,
                    'total_price' : self.subscription_order_line_ids.total_price
                }))
            ],
        })
        if self.sale_order_template_id.invoice_creation in ['draft',
                                                            'confirmed',
                                                            'sent']:
            order.action_post()
        if self.check_upsell_renewal is True:
            order.message_post(
                body=_('Subscription order is renewed from the order %s',
                       self._get_html_link()),
                message_type='comment', subtype_xmlid='mail.mt_comment')
        else:
            order.message_post(
                body=_('Subscription order is Upsell from the order %s',
                       self._get_html_link()),
                message_type='comment', subtype_xmlid='mail.mt_comment')

        return {
            'name': 'Subscription Order',
            'view_type': 'form',
            'view_mode': 'form',
            'payment_reference': self.id,
            'res_model': 'subscription.order',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref(
                'cyllo_subscription.view_subscription_order_form').id,
            'res_id': order.id
        }

    def action_close_subscription(self):
        """Calling wizard to close the subscription"""
        return {
            'name': 'Close Reason',
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.close',
            'view_mode': 'form',
            'context': {'default_subscription_order_id': self.id},
            'target': 'new',
        }

    def consolidated_invoice(self):
        """Create consolidated invoice from multiple subscription orders"""
        inv_id = []
        records = self.browse(self.env.context.get('active_ids')).filtered(
            lambda o: o.state_subscription != 'churned').ids
        for key, value in groupby(self.env['subscription.order'].search_read(
                [('id', 'in', records)], ['partner_id']),
                                  key=itemgetter('partner_id')):
            lst = [val['id'] for val in value]
            orders = self.browse(lst)
            partner = []
            product = {}
            for order in orders:
                partner.append(order.partner_id.id)
                product = {
                    'key': order.subscription_order_line_ids
                }
            inv = self.env['account.move'].create({
                'partner_id': partner[0],
                'move_type': 'out_invoice',
                'payment_reference': self.ids,
                'invoice_line_ids': [
                    (fields.Command.create({
                        'product_id': product['key'].product_id.id,
                        'price_unit': product['key'].subtotal,
                        'tax_ids': product['key'].tax_ids.ids,
                    }))],
            })
            inv_id.append(inv.id)
        return {
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', inv_id)],
            'target': 'current'
        }

    def _get_report_base_filename(self):
        """providing name for report in the portal"""
        self.ensure_one()
        return 'Subscription Report- %s' % self.name

    def _creation_message(self):
        """Creation message"""
        if self.sale_order_id:
            return _("Subscription order is Created from %s",
                     self.sale_order_id._get_html_link())
        return super()._creation_message()

    def check_subscription_renewal(self):
        """Check the orders that going to renew and sent mail to the partner"""
        records = self.search([('renewal_date', '<=',
                                fields.Datetime.now() + relativedelta(days=1)),
                               ('state_subscription', '!=', 'churned')])
        records.state_subscription = 'renew'
        for record in records:
            body = self.env.ref(
                'cyllo_subscription.mail_template_subscription_order_due_reminder_email')
            body['email_to'] = record.partner_id.email
            body.sudo().send_mail(record.id, force_send=True)

    def check_subscription_close(self):
        records = self.search([('end_date', '<',fields.Datetime.now()),('state_subscription', '!=', 'churned')])
        if records:
            records.write({'state_subscription': 'churned'})
            for record in records:
                body = self.env.ref(
                    'cyllo_subscription.mail_template_subscription_order_closed_reminder_email')
                body['email_to'] = record.partner_id.email
                body.sudo().send_mail(record.id, force_send=True)
                record.message_post(
                    body=_('Subscription order has been closed.'),
                    message_type='comment', subtype_xmlid='mail.mt_comment')


