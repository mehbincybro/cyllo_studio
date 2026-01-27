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
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetLost(models.TransientModel):
    """Model for asset lost"""
    _name = 'asset.lost'
    _description = 'Asset Lost'

    asset_asset_id = fields.Many2one('asset.asset', string="Asset")
    loss_account_id = fields.Many2one('account.account')
    lost_date = fields.Date(default=fields.Date.context_today, required=True)
    note = fields.Text()
    is_scrap = fields.Boolean()
    depreciated_amount = fields.Float()
    current_depreciated_amount = fields.Float()
    is_posted = fields.Boolean()

    @api.onchange('loss_account_id')
    def _onchange_loss_account_id(self):
        """Function for checking loss account"""
        if self.asset_asset_id.asset_depreciation_account_id.id == self.loss_account_id.id:
            raise UserError(_('You cannot select the same account as the Asset Depreciation Account.'))

    def action_submit(self):
        """Button action for submit the asset lost"""
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
            'date': self.lost_date,
            'line_ids': [fields.Command.create(lines) for lines in move_lines],
        }
        self.env['account.move'].create(vals)
        if self.is_scrap:
            self.asset_asset_id.status = 'disposed'
        else:
            self.asset_asset_id.status = 'lost'
            child_assets = self.env['asset.asset'].search([('parent_id','=',self.asset_asset_id.id)])
            child_assets.write({'status': 'lost','is_lost' :True})
        self.asset_asset_id.is_lost = True

    def calculate_day_amount(self, unposted_entries):
        """Function for calculating day amount"""
        if self.asset_asset_id.duration_period == 'month':
            current_depreciation_entry = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda d: d.date.month == self.lost_date.month and d.date.year == self.lost_date.year).mapped(
                'amount_total_signed'))
            days = calendar.monthrange(self.asset_asset_id.depreciation_date.year,
                                       self.asset_asset_id.depreciation_date.month)[1]
            depreciated_days = self.lost_date.day
        else:
            current_depreciation_entry = sum(self.asset_asset_id.depreciated_entry_ids.filtered(
                lambda d: d.date.year == self.lost_date.year).mapped('amount_total_signed'))
            start_date = datetime(self.lost_date.year, 1, 1).date()
            depreciated_days = (self.lost_date - start_date).days + 1
            days = 366 if calendar.isleap(self.asset_asset_id.depreciation_date.year) else 365
        day_amount = current_depreciation_entry / days
        depreciated_amount = depreciated_days * day_amount
        self.depreciated_amount = depreciated_amount
        self.current_depreciated_amount = depreciated_amount
        undepreciated_amount = current_depreciation_entry - depreciated_amount
        return day_amount, current_depreciation_entry, depreciated_amount, undepreciated_amount

    def update_depreciation_entries(self):
        """Function for updating depreciation entries"""
        posted_entries = self.asset_asset_id.depreciated_entry_ids.filtered(
            lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id)
        unposted_entries = self.asset_asset_id.depreciated_entry_ids.filtered(
            lambda e: e.state == 'draft')
        day_amount, current_depreciation_entry, depreciated_amount, undepreciated_amount = self.calculate_day_amount(
            unposted_entries)
        posted_entries_amount = sum(posted_entries.mapped('amount_total_signed'))
        unposted_entries_amount = sum(unposted_entries.mapped('amount_total_signed'))
        if posted_entries:
            previous_amount = posted_entries_amount
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
                'date': self.lost_date,
                'accumulative_depreciation': previous_amount,
                'salvage_value': salvage_value,
            })
            amount = unposted_entries_amount - depreciated_amount
            previous_amount = previous_amount + amount
            salvage_value = salvage_value - amount
            modify_vals.append({
                'depreciation_expense': amount,
                'depreciation_id': self.asset_asset_id.id,
                'date': self.lost_date,
                'accumulative_depreciation': previous_amount,
                'salvage_value': salvage_value,
            })
        for depreciation in modify_vals:
            if depreciation['depreciation_expense'] > 0 :
                if depreciation['salvage_value'] == 0:
                    depreciation['journal_reference'] = '/'

                line = self.env['asset.depreciation.line'].create(depreciation)
                self.asset_asset_id.depreciation_line_ids = [fields.Command.link(line.id)]
                if  depreciation['salvage_value'] != 0:
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
                        'account_id': self.asset_asset_id.asset_expense_account_id.id,
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
                    past_journals = journal_items.filtered(lambda x: x.invoice_date_due <= self.lost_date)
                    if past_journals:
                        past_journals._post()
