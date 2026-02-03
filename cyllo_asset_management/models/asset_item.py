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


class AssetItem(models.Model):
    """Model for asset items"""
    _name = 'asset.item'
    _description = 'Account Item'
    _inherit = ['mail.thread']

    name = fields.Char(string="Assets", required=True)
    # asset_type_id = fields.Many2one("asset.type", required=True)
    # brand_ids = fields.Many2many('asset.brand', compute='_compute_brand_ids')
    brand = fields.Char(string="Brand")
    date = fields.Date(default=fields.Date.context_today, required=True)
    vendor_id = fields.Many2one("res.partner", string="Purchase From", copy=False)
    serial_no = fields.Char(string="Serial No.")
    purchase_date = fields.Date(default=fields.Date.context_today, required=True)
    depreciation_method = fields.Selection(
        [('straight_line', 'Straight Line'), ('declining_balance', 'Declining Balance'),
         ('double_declining', 'Double Declining Balance'), ('declining_straight_line', 'Declining and Straight Line')],
        string='Method', required=True)
    is_auto_calculate = fields.Boolean(string='Auto Calculate', default=True)
    depreciating_factor = fields.Float(default=30)
    method_duration = fields.Integer(string="Duration", tracking=True, default=1)
    duration_period = fields.Selection([('month', 'Month'), ('year', 'Year')], tracking=True, default='year',
                                       required=True)
    computation_method = fields.Selection(
        [('no_prorata', 'No Prorata'), ('constant_period', 'Constant Period'), ('daily_compute', 'Daily Computation')],
        'Computation', default='no_prorata', tracking=True, required=True)
    prorata_date = fields.Date(default=fields.Date.context_today)
    fixed_asset_account_id = fields.Many2one('account.account', required=True,
                                             domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_depreciation_account_id = fields.Many2one('account.account', string='Depreciation Asset Account',
                                                    required=True,
                                                    domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_expense_account_id = fields.Many2one('account.account', required=True,
                                               domain="[('account_type', '=', 'expense')]")
    asset_journal_id = fields.Many2one('account.journal', required=True)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    asset_loss_account_id = fields.Many2one('account.account', required=True)


    # @api.depends('asset_type_id')
    # def _compute_brand_ids(self):
    #     """Function for accessing the brands based on the asset type"""
    #     for rec in self:
    #         rec.brand_ids = False
    #         if rec.asset_type_id:
    #             rec.brand_ids = rec.asset_type_id.brand_ids.ids

    @api.constrains('method_duration')
    def _onchange_method_duration(self):
        """Function for checking method duration"""
        if self.method_duration <= 0:
            raise UserError(_('The Duration period should be greater than 0'))
