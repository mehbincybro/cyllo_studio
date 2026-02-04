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
import math
import calendar
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetRental(models.Model):
    """Model for asset rental"""
    _name = 'asset.rental'
    _description = 'Rental Assets'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one('asset.asset', required=True)
    start_date = fields.Date(string="Period", required=True, tracking=True,
                             help="Select an Asset before setting the period. Start and End Dates must be after the Asset's Purchase Date, and End Date must be later than Start Date.")
    end_date = fields.Date(string="End", required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', required=True, tracking=True)
    email = fields.Char(related='customer_id.email')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    payment_terms = fields.Selection(
        [('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly'), ('year', 'Yearly')],
        required=True)
    payment_type = fields.Selection([('complete', 'Based on Payment Terms'), ('usage', 'Based on Usage')],
                                    default='complete', required=True)
    rent_amount = fields.Float(string='Amount', compute='_compute_rent_amount', store=True)
    status = fields.Selection(
        [('draft', 'Draft'), ('rent', 'Rent'), ('return', 'Return'), ('cancel', 'Cancel')], default='draft',
        tracking=True, copy=False)
    reservation_id = fields.Many2one('asset.reservation')
    invoice_count = fields.Integer(string='Invoice', copy=False, compute='_compute_invoice_count')
    is_return = fields.Boolean(copy=False)
    is_invoice = fields.Boolean(copy=False)
    active = fields.Boolean(default=True)
    asset_ids = fields.Many2many('asset.asset', compute="_compute_asset_ids")

    @api.depends('company_id')
    def _compute_asset_ids(self):
        """Function for showing reserved assets only to user"""
        for record in self:
            if (self.env.user.has_group('account.group_account_manager') or
                    self.env.user.has_group('cyllo_asset_management.group_cyllo_asset_admin')):
                record.asset_ids = self.env['asset.asset'].search([])
            elif self.env.user.has_group('cyllo_asset_management.group_cyllo_asset_users'):
                record.asset_ids = self.env['asset.reservation'].search([('employee_id.user_id', '=', self.env.user.id),
                                                                         ('status', '=', 'reserve')]).mapped('asset_id')

    @api.depends('payment_terms')
    def _compute_rent_amount(self):
        """Function for accessing the rent amount"""
        for rec in self:
            if rec.payment_terms == 'day':
                rec.rent_amount = rec.asset_id.day_amount
            elif rec.payment_terms == 'week':
                rec.rent_amount = rec.asset_id.week_amount
            elif rec.payment_terms == 'month':
                rec.rent_amount = rec.asset_id.month_amount
            elif rec.payment_terms == 'year':
                rec.rent_amount = rec.asset_id.year_amount

    def _compute_invoice_count(self):
        """Function for computing the invoice count"""
        self.invoice_count = self.env['account.move'].search_count(
            [('rent_id', '=', self.id), ('ref', '=', self.asset_id.name)])

    @api.onchange('start_date', 'end_date')
    def _onchange_lease_date(self):
        """Function for checking the start and end date"""
        purchase_date = self.sudo().asset_id.date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise UserError(_('The End Date is greater than the Start Date'))
            elif (self.start_date < purchase_date) or (self.end_date < purchase_date):
                raise UserError(
                    _(f'The Asset id Purchased on {purchase_date}.The Start Date and End Date should be greater than the Purchase Date'))
            if self.reservation_id:
                reserved_date = self.reservation_id.start_date
                if self.start_date < reserved_date:
                    raise UserError(
                        _(f'The Asset is Reserved on {reserved_date}. The Start Date should be greater than the Reserved start Date'))

    def unlink(self):
        """Function the unlink the lease records"""
        for rec in self:
            if rec.status == 'rent':
                raise UserError(_('You cannot delete the record that is in Rent state.'))
        else:
            self.asset_id.is_rental = False
            return super().unlink()

    def action_create_rental(self):
        """Button action for create rental for the assets"""
        asset_id=self.sudo().asset_id
        if not asset_id.is_rental_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a rental asset.'))
        elif asset_id.is_rental:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for the Rent.'))
        open_requests = self.env['maintenance.request'].sudo().search([('asset_id', '=', self.asset_id.id),
                                                                       ('stage_done', '=', False), ])
        if open_requests:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            self.status = 'rent'
            context = {
                'asset': asset_id.name,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'customer': self.customer_id.name
            }
            template = self.env.ref(
                'cyllo_asset_management.mail_template_asset_rental',
                raise_if_not_found=False)
            email_values = {
                'email_to': self.email
            }
            template.with_context(**context).send_mail(res_id=self.id, email_values=email_values, force_send=True)
            asset_id.is_rental = True
            asset_id.status = 'rented'
            if self.reservation_id:
                asset_id.is_reserve = True
                asset_id.status = 'reserved'
                self.reservation_id.write({
                    'status': 'rent'})
                # Generate Invoice
            days = 0
            start_date = self.start_date
            end_date = self.end_date
            invoice_date = start_date
            invoice_days = 0
            if self.payment_terms == 'day':
                invoice_days = (end_date - start_date).days + 1
            elif self.payment_terms == 'week':
                invoice_days = ((end_date - start_date).days + 1) / 7
            elif self.payment_terms == 'month':
                while start_date <= end_date:
                    total_month_days = calendar.monthrange(start_date.year, start_date.month)[1]
                    start_date = start_date + relativedelta(days=total_month_days)
                    invoice_days += 1
            else:
                while start_date <= end_date:
                    total_year_days = 366 if calendar.isleap(start_date.year) else 365
                    start_date = start_date + relativedelta(days=total_year_days)
                    invoice_days += 1
            invoice_days = math.ceil(invoice_days)
            rent_amount = self.rent_amount
            for period in range(invoice_days):
                current_date = invoice_date
                if self.payment_terms == 'day':
                    invoice_date = invoice_date + relativedelta(days=1)
                elif self.payment_terms == 'week':
                    days = 7
                    invoice_date = invoice_date + relativedelta(days=days)
                elif self.payment_terms == 'month':
                    days = calendar.monthrange(invoice_date.year, invoice_date.month)[1]
                    invoice_date = invoice_date + relativedelta(days=days)
                else:
                    days = 366 if calendar.isleap(invoice_date.year) else 365
                    invoice_date = invoice_date + relativedelta(days=days)
                if invoice_date > end_date:
                    invoice_date = end_date
                if self.payment_terms == 'day':
                    amount = rent_amount
                else:
                    if self.payment_type == 'usage':
                        total_days = (invoice_date - current_date).days + 1
                        if total_days < days:
                            days = (end_date - current_date).days + 1
                            rent_amount = self.asset_id.day_amount
                        amount = days * rent_amount
                    else:
                        total_invoicing_days = (invoice_date - current_date).days
                        total_days = days if total_invoicing_days < days else total_invoicing_days
                        amount = total_days * rent_amount
                if amount <= 0:
                    break
                else:
                    accounting_date = invoice_date + relativedelta(days=-1)
                    last_period = period + 1
                    self.env['account.move'].create({
                        'asset_id': False,
                        'ref': self.asset_id.name,
                        'partner_id': self.customer_id.id,
                        'invoice_date_due': end_date if last_period == invoice_days else accounting_date,
                        'invoice_date': end_date if last_period == invoice_days else accounting_date,
                        'move_type': 'out_invoice',
                        'rent_id': self.id,
                        'state': 'draft',
                        'auto_post': 'at_date',
                        'invoice_line_ids': [fields.Command.create({
                            'name': self.asset_id.asset_item_id.name,
                            'move_type': 'out_invoice',
                            'price_unit': int(amount),
                        })]
                    })
            self.is_invoice = True

    def action_view_invoice(self):
        """Function for viewing rental invoices"""
        return {
            'name': 'Invoice',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('ref', '=', self.asset_id.name), ('rent_id', '=', self.id)]
        }

    def action_return_asset(self):
        """Button action for returning the assets"""
        asset_id=self.sudo().asset_id
        invoice = self.env['account.move'].search([('rent_id', '=', self.id), ('payment_state', '!=', 'paid')])
        if invoice:
            raise UserError(
                _('You cannot complete this operation, The invoices amount is not paid'))
        else:
            self.is_return = True
            asset_id.is_rental = False
            self.status = 'return'
            if self.reservation_id:
                if self.reservation_id.end_date > fields.date.today():
                    asset_id.is_reserve = True
                    self.reservation_id.write({
                        'status': 'reserve'})
                else:
                    asset_id.is_reserve = False
                    self.reservation_id.write({
                        'status': 'cancel'})
            if asset_id.is_reserve == True:
                asset_id.status = 'reserved'
            elif asset_id.is_confirm == True:
                asset_id.status = 'running'
            else:
                asset_id.status = 'draft'

    def action_cancel(self):
        """Button action for cancel the rental assets"""
        self.status = 'cancel'
        self.asset_id.is_rental = False
        if self.reservation_id:
            self.asset_id.is_reserve = False
            self.reservation_id.write({
                'status': 'cancel'})

    def action_reset_to_draft(self):
        """Button action for reset the rental assets to draft state"""
        if self.asset_id.status in ('sell', 'disposed', 'cancel', 'lost', 'rented'):
            raise UserError(_(f'You cannot reset to draft.The related asset is in {self.asset_id.status} state.'))
        self.status = 'draft'
        self.is_return = False
        self.is_invoice = False
        invoice = self.env['account.move'].search([('rent_id', '=', self.id)])
        if invoice.filtered(lambda e: e.state != 'draft'):
            raise UserError(_('You cannot reset to draft, The related rental invoice is already posted'))
        else:
            invoice.unlink()

    def _send_asset_rental_invoice_reminder_mail(self):
        """Function for sending email to the customers regarding about rental"""
        due_invoice = self.env['account.move'].search([('rent_id.status', '=', 'rent'), ('state', '=', 'draft')])
        for inv in due_invoice:
            remainder_date = inv.invoice_date_due + relativedelta(days=-3)
            if fields.Date.today() == remainder_date:
                context = {
                    'asset': inv.ref,
                    'due_date': inv.invoice_date_due,
                    'customer': inv.partner_id.name
                }
                template = self.env.ref(
                    'cyllo_asset_management.mail_template_assent_rental_invoice_due_reminder',
                    raise_if_not_found=False)
                email_values = {
                    'email_to': inv.partner_id.email
                }
                template.with_context(**context).send_mail(res_id=inv.id, email_values=email_values, force_send=True)
