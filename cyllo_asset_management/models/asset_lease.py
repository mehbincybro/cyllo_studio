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

from odoo import _, api, models, fields
from odoo.exceptions import UserError


class AssetLease(models.Model):
    """Model for the asset lease"""
    _name = 'asset.lease'
    _description = 'Lease Assets'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one('asset.asset', required=True)
    start_date = fields.Date(string="Period", required=True, tracking=True, help="Select an Asset before setting the period. Start and End Dates must be after the Asset's Purchase Date, and End Date must be later than Start Date.")
    end_date = fields.Date(string="End", required=True, tracking=True)
    customer_id = fields.Many2one('res.partner', required=True, tracking=True)
    email = fields.Char(related='customer_id.email')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    status = fields.Selection(
        [('draft', 'Draft'), ('lease', 'Lease'), ('return', 'Return'), ('cancel', 'Cancel')], default='draft',
        tracking=True, copy=False)
    reservation_id = fields.Many2one('asset.reservation')
    lease_amount = fields.Float(string='Amount', required=True)
    is_return = fields.Boolean(copy=False)
    is_invoice = fields.Boolean(copy=False)
    active = fields.Boolean(default=True)

    @api.onchange('lease_amount')
    def _onchange_lease_amount(self):
        """Function for checking the lease amount"""
        if self.lease_amount and self.lease_amount < 0:
            self.lease_amount = abs(self.lease_amount)

    @api.onchange('start_date', 'end_date')
    def _onchange_lease_date(self):
        """Function for checking the start and end date"""
        purchase_date = self.asset_id.asset_item_id.purchase_date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise UserError(_('The End Date is greater than the Start Date'))
            elif (self.start_date < purchase_date) or (self.end_date < purchase_date):
                raise UserError(
                    _(f'The Asset id Purchased on {purchase_date}.The Start Date and End Date should be greater than the Purchase Date'))

    def unlink(self):
        """Function for unlink the lease records"""
        for rec in self:
            if rec.status == 'lease':
                raise UserError(_('You cannot delete the record that is in leased state.'))
        else:
            self.asset_id.is_lease = False
            return super().unlink()

    def action_create_lease(self):
        """Button action creating the lease"""
        if not self.asset_id.is_lease_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a lease asset.'))
        elif self.asset_id.is_lease:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for the Lease.'))
        elif self.lease_amount and self.lease_amount == 0:
            raise UserError(_('You cannot complete this operation, Please specify the lease amount.'))
        repair_asset = self.env['account.asset.repair'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'repairing'])])
        maintenance_asset = self.env['account.asset.maintenance'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'ongoing'])])
        if (maintenance_asset and self.start_date <= maintenance_asset.scheduled_date) or (
                maintenance_asset and self.end_date <= maintenance_asset.scheduled_date) or (
                repair_asset and self.start_date <= repair_asset.scheduled_date) or (
                repair_asset and self.end_date <= repair_asset.scheduled_date):
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            self.status = 'lease'
            context = {
                'asset': self.asset_id.name,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'customer': self.customer_id.name
            }
            template = self.env.ref(
                'cyllo_asset_management.mail_template_asset_leasing',
                raise_if_not_found=False)
            email_values = {
                'email_to': self.email
            }
            template.with_context(**context).send_mail(res_id=self.id, email_values=email_values, force_send=True)
            self.asset_id.is_lease = True
            if self.reservation_id:
                self.asset_id.is_reserve = False
                self.reservation_id.write({
                    'status': 'lease'})
            self.env['account.move'].create({
                'asset_id': False,
                'ref': self.asset_id.name,
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'state': 'draft',
                'lease_id': self.id,
                'invoice_line_ids': [fields.Command.create({
                    'name': self.asset_id.asset_item_id.name,
                    'move_type': 'out_invoice',
                    'price_unit': self.lease_amount,
                })]
            })
            self.is_invoice = True

    def action_view_invoice(self):
        """Function for viewing the lease invoice"""
        lease_invoice = self.env['account.move'].search([('ref', '=', self.asset_id.name), ('lease_id', '=', self.id)])
        if len(lease_invoice) > 1:
            return {
                'name': 'Invoice',
                'view_mode': 'tree, form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', lease_invoice.ids)],
            }
        else:
            return {
                'name': 'Invoice',
                'view_mode': 'form',
                'res_id': lease_invoice.id,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
            }

    def action_return_asset(self):
        """Button action returning the leased assets"""
        invoice = self.env['account.move'].search([('lease_id', '=', self.id), ('payment_state', '!=', 'paid')])
        if invoice:
            raise UserError(
                _('You cannot complete this operation, The invoice is not paid'))
        else:
            self.is_return = True
            self.status = 'cancel'
            self.asset_id.is_lease = False
            if self.reservation_id:
                self.asset_id.is_reserve = False
                self.reservation_id.write({
                    'status': 'cancel'})

    def action_reset_to_draft(self):
        """Function for reset the leased assets to the draft state"""
        if self.asset_id.status in ('sell', 'disposed', 'cancel', 'lost'):
            raise UserError(_(f'You cannot reset to draft.The related asset is in {self.asset_id.status} state.'))
        self.status = 'draft'

    def _send_lease_asset_return_reminder_mail(self):
        """Function for sending mails to the customer regarding the lease"""
        lease_asset = self.search([('status', '=', 'lease')])
        for asset in lease_asset:
            remainder_date = asset.end_date + relativedelta(days=-3)
            if fields.Date.today() == remainder_date:
                context = {
                    'asset': asset.asset_id.name,
                    'end_date': asset.end_date,
                    'customer': asset.customer_id.name
                }
                template = self.env.ref(
                    'cyllo_asset_management.mail_template_leased_assent_return_reminder',
                    raise_if_not_found=False)
                email_values = {
                    'email_to': asset.customer_id.email
                }
                template.with_context(**context).send_mail(res_id=asset.id, email_values=email_values, force_send=True)
