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
import calendar

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetSellDispose(models.Model):
    """Model for Asset sell or dispose"""
    _name = 'asset.sell.dispose'
    _description = 'Sell and Dispose the Assets'
    _rec_name = 'asset_asset_id'
    _inherit = ['mail.thread']

    asset_asset_id = fields.Many2one('asset.asset', required=True)
    asset_action = fields.Selection([('sell', 'Sell'), ('dispose', 'Dispose')], string="Action", default='sell',
                                    tracking=True)
    loss_account_id = fields.Many2one('account.account')
    invoice_ids = fields.Many2many('account.move', domain="[('move_type', '=', 'out_invoice')]")
    invoice_line_ids = fields.Many2many('account.move.line')
    date = fields.Date(default=fields.Date.context_today, required=True)
    note = fields.Text()
    is_done = fields.Boolean(string='Done', copy=False)
    is_entry = fields.Boolean(related='asset_asset_id.is_entry', copy=False)
    depreciated_amount = fields.Float()
    current_depreciated_amount = fields.Float()
    is_posted = fields.Boolean()

    @api.constrains('date')
    def _constrains_date(self):
        for record in self:
            purchase_date = record.asset_asset_id.asset_item_id.purchase_date
            if record.date and record.date < purchase_date:
                raise UserError(
                    _(f'The Asset is Purchased on {purchase_date}. The Date should be greater or equal to the Purchase Date'))

    @api.onchange('loss_account_id')
    def _onchange_loss_account_id(self):
        """Function for checking the loss account"""
        if self.asset_asset_id.asset_depreciation_account_id.id == self.loss_account_id.id:
            raise UserError(_('You cannot select the same account as the Asset Depreciation Account.'))

    def action_sell(self):
        """Button action for selling the assets"""
        if not self.is_entry:
            self.asset_asset_id.status = 'sell'
        else:
            unposted_entries_amount = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft').mapped('amount_total_signed'))
            posted_entries_amount = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id).mapped(
                'amount_total_signed'))
            invoice_line_amount = sum(self.invoice_line_ids.mapped('price_subtotal'))
            sell_amount = invoice_line_amount - (posted_entries_amount + unposted_entries_amount)
            self.update_depreciation_entries()
            self.asset_asset_id.depreciated_entry_ids.filtered(lambda l: l.state == 'draft').unlink()
            self.asset_asset_id.depreciation_line_ids.filtered(lambda e: not e.journal_reference).unlink()
            move_lines = []
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.fixed_asset_account_id.id,
                'credit': posted_entries_amount + unposted_entries_amount,
                'debit': 0.0,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.asset_depreciation_account_id.id,
                'credit': 0.0,
                'debit': self.depreciated_amount,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.invoice_line_ids.account_id.id,
                'debit': invoice_line_amount,
                'credit': 0.0,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.loss_account_id.id,
                'credit': sell_amount + self.depreciated_amount,
                'debit': 0.0,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            vals = {
                'move_type': 'entry',
                'asset_asset_id': self.asset_asset_id.id,
                'ref': _("%s: Sell", self.asset_asset_id.name),
                'date': self.date,
                'line_ids': [fields.Command.create(lines) for lines in move_lines],
            }
            self.env['account.move'].create(vals)
            self.is_done = True
            self.asset_asset_id.is_sell = True
            self.asset_asset_id.status = 'sell'

    def action_dispose(self):
        """Button action for disposing the assets"""
        if not self.is_entry:
            self.asset_asset_id.status = 'disposed'
        else:
            unposted_entries_amount = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft').mapped('amount_total_signed'))
            posted_entries_amount = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id).mapped(
                'amount_total_signed'))
            self.update_depreciation_entries()
            self.asset_asset_id.depreciated_entry_ids.filtered(lambda l: l.state == 'draft').unlink()
            self.asset_asset_id.depreciation_line_ids.filtered(lambda e: not e.journal_reference).unlink()
            move_lines = []
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.fixed_asset_account_id.id,
                'debit': 0.0,
                'credit': unposted_entries_amount + posted_entries_amount,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.asset_depreciation_account_id.id,
                'credit': 0.0,
                'debit': self.depreciated_amount,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            if not self.is_posted:
                move_lines.append({
                    'name': self.asset_asset_id.name,
                    'account_id': self.loss_account_id.id,
                    'credit': 0.0,
                    'debit': unposted_entries_amount - self.current_depreciated_amount,
                    'currency_id': self.asset_asset_id.currency_id.id,
                })
            vals = {
                'move_type': 'entry',
                'asset_asset_id': self.asset_asset_id.id,
                'ref': _("%s: Dispose", self.asset_asset_id.name),
                'date': self.date,
                'line_ids': [fields.Command.create(lines) for lines in move_lines],
            }
            self.env['account.move'].create(vals)
            self.is_done = True
            self.asset_asset_id.is_dispose = True
            self.asset_asset_id.status = 'disposed'

    def calculate_day_amount(self, unposted_entries):
        """Function for calculating the day amount"""
        if self.asset_asset_id.duration_period == 'month':
            current_depreciation_entry = unposted_entries.filtered(
                lambda d: d.date.month == self.date.month and d.date.year == self.date.year)
            days = calendar.monthrange(self.asset_asset_id.depreciation_date.year,
                                       self.asset_asset_id.depreciation_date.month)[1]
            depreciated_days = self.date.day
        else:
            current_depreciation_entry = self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda d: d.date.year == self.date.year)
            start_date = self.date.replace(day=1)
            depreciated_days = (self.date - start_date).days + 1
            days = 366 if calendar.isleap(self.asset_asset_id.depreciation_date.year) else 365
        day_amount = current_depreciation_entry.amount_total_signed / days
        depreciated_amount = depreciated_days * day_amount
        self.depreciated_amount = depreciated_amount
        self.current_depreciated_amount = depreciated_amount
        undepreciated_amount = current_depreciation_entry.amount_total_signed - depreciated_amount
        return day_amount, current_depreciation_entry, depreciated_amount, undepreciated_amount

    def update_depreciation_entries(self):
        """Function for updating the depreciation entries"""
        depreciated_amount = 0
        posted_entries = self.asset_asset_id.depreciated_entry_ids.filtered(
            lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id)
        unposted_entries = self.asset_asset_id.depreciated_entry_ids.filtered(
            lambda e: e.state == 'draft')
        if unposted_entries:
            day_amount, current_depreciation_entry, depreciated_amount, undepreciated_amount = self.calculate_day_amount(
                unposted_entries)
        posted_entries_amount = sum(posted_entries.mapped('amount_total_signed'))
        unposted_entries_amount = sum(unposted_entries.mapped('amount_total_signed'))
        if posted_entries:
            previous_amount = posted_entries_amount + depreciated_amount
            salvage_value = unposted_entries_amount - depreciated_amount
            self.depreciated_amount += posted_entries_amount
        else:
            previous_amount = depreciated_amount
            salvage_value = unposted_entries_amount - depreciated_amount
        modify_vals = []
        if not self.is_posted:
            modify_vals.append({
                'depreciation_expense': depreciated_amount,
                'depreciation_id': self.asset_asset_id.id,
                'date': self.date,
                'accumulative_depreciation': previous_amount,
                'salvage_value': salvage_value,
            })
            amount = unposted_entries_amount - depreciated_amount
            previous_amount = previous_amount + amount
            salvage_value = salvage_value - amount
            modify_vals.append({
                'depreciation_expense': amount,
                'depreciation_id': self.asset_asset_id.id,
                'date': self.date,
                'accumulative_depreciation': previous_amount,
                'salvage_value': salvage_value,
            })
        for depreciation in modify_vals:
            line = self.env['asset.depreciation.line'].create(depreciation)
            self.asset_asset_id.depreciation_line_ids = [fields.Command.link(line.id)]
            move_lines = []
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.asset_depreciation_account_id.id,
                'credit': depreciation['depreciation_expense'],
                'debit': 0.0,
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            move_lines.append({
                'name': self.asset_asset_id.name,
                'account_id': self.asset_asset_id.asset_depreciation_account_id.id,
                'credit': 0.0,
                'debit': depreciation['depreciation_expense'],
                'currency_id': self.asset_asset_id.currency_id.id,
            })
            vals = {
                'move_type': 'entry',
                'asset_asset_id': self.asset_asset_id.id,
                'ref': _("%s: Depreciation", self.asset_asset_id.name),
                'date': depreciation['date'],
                'invoice_date_due': depreciation['date'],
                'journal_id': self.asset_asset_id.asset_journal_id.id,
                'auto_post': 'at_date',
                'currency_id': self.asset_asset_id.currency_id.id,
                'depreciation_line_id': line.id,
                'line_ids': [fields.Command.create(lines) for lines in move_lines],
            }
            journal_items = self.asset_asset_id.depreciated_entry_ids.create(vals)
            past_journals = journal_items.filtered(lambda x: x.invoice_date_due <= self.date)
            if past_journals:
                past_journals._post()
