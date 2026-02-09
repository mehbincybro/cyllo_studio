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
from odoo.fields import Date
from odoo.tools.date_utils import end_of


class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset Assets'
    _inherit = ['mail.thread']

    name = fields.Char(string="Asset", required=True)
    asset_item_id = fields.Many2one("asset.item")
    brand_id = fields.Many2one(string="Brand", comodel_name='asset.brand')
    serial_no = fields.Char(string="Serial No.")
    vendor_id = fields.Many2one("res.partner", string="Purchase From", copy=False)
    date = fields.Date(string="Purchase Date", default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    status = fields.Selection(
        [('draft', 'Draft'), ('running', 'Running'), ('reserved', 'Reserved'), ('leased', 'Leased'),
         ('assigned', 'Assigned'), ('rented', 'Rented'), ('sell', 'Sell'), ('disposed', 'Dispose'),
         ('cancel', 'Cancelled')],
        default="draft", copy=False, tracking=True)
    is_confirm = fields.Boolean(string="Confirmed", copy=False)
    is_modify = fields.Boolean(string="Confirmed", copy=False)
    is_reserve = fields.Boolean(string="Reserved", copy=False)
    is_assign = fields.Boolean(string="Assigned", copy=False)
    is_lease = fields.Boolean(string="Leased", copy=False)
    is_rental = fields.Boolean(string="Rental", copy=False)
    is_repair = fields.Boolean(string="Repair", copy=False)
    is_maintenance = fields.Boolean(string="Maintenance", copy=False)
    is_sell = fields.Boolean(string="Sell", copy=False)
    is_dispose = fields.Boolean(string="Dispose", copy=False)
    is_lost = fields.Boolean(string="Loss", copy=False)
    is_depreciate = fields.Boolean(string="Depreciate", copy=False)
    is_entry = fields.Boolean(string="Entry", copy=False)
    is_lease_asset = fields.Boolean()
    is_rental_asset = fields.Boolean()
    is_revaluate = fields.Boolean()
    is_decrease_value = fields.Boolean()
    day_amount = fields.Float()
    week_amount = fields.Float()
    month_amount = fields.Float()
    year_amount = fields.Float()
    parent_id = fields.Many2one('asset.asset')
    maintenance_state = fields.Selection([('maintenance', 'Under Maintenance'), ('repair', 'Under Repair')],
                                         compute='_compute_maintenance_state', store=False)
    depreciation_method = fields.Selection(
        [('straight_line', 'Straight Line'), ('declining_balance', 'Declining Balance'),
         ('double_declining', 'Double Declining Balance'), ('declining_straight_line', 'Declining and Straight Line')],
        string='Method', readonly=False, required=True, default='straight_line')
    depreciation_date = fields.Date(default=fields.Date.context_today, tracking=True, string='Depreciation date')
    method_duration = fields.Integer(string="Duration", tracking=True, default=1, readonly=False)
    is_auto_calculate = fields.Boolean(string='Auto Calculate')
    depreciating_factor = fields.Float(default=30)
    duration_period = fields.Selection([('month', 'Month'), ('year', 'Year')], tracking=True, default='year',
                                       required=True)
    original_value = fields.Float(required=True)
    salvage_value = fields.Float(required=True, string='Depreciatable Value')
    modify_value = fields.Float()
    depreciation_line_ids = fields.One2many('asset.depreciation.line', 'depreciation_id',
                                            string='Asset Depreciation Line')
    fixed_asset_account_id = fields.Many2one('account.account', required=True,
                                             domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_depreciation_account_id = fields.Many2one('account.account', string='Depreciation Asset Account',
                                                    required=True,
                                                    domain="[('account_type', 'in', ('asset_current', 'asset_fixed'))]")
    asset_expense_account_id = fields.Many2one('account.account', required=True,
                                               domain="[('account_type', '=', 'expense')]")
    asset_loss_account_id = fields.Many2one('account.account', required=True)
    asset_journal_id = fields.Many2one('account.journal', required=True,
                                       domain="[('type', '=', 'general')]")
    depreciated_entry_ids = fields.One2many('account.move', 'asset_asset_id', string='Depreciation Lines')
    modified_asset_ids = fields.Many2many('asset.asset', "asset_sub_table", 'asset_1', 'asset_2')
    computation_method = fields.Selection(
        [('no_prorata', 'No Prorata'), ('constant_period', 'Constant Period'), ('daily_compute', 'Daily Computation')],
        'Computation', tracking=True, readonly=False, required=True, default='no_prorata')
    prorata_date = fields.Date(default=fields.Date.context_today)
    entry_count = fields.Integer(compute='_compute_entry_count')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count')
    modified_count = fields.Integer(compute='_compute_modified_count')
    invoice_id = fields.Many2one('account.move')
    invoice_line_id = fields.Many2one('account.move.line')
    active = fields.Boolean(default=True)
    depreciation_duration = fields.Integer()
    total_depreciation_days = fields.Integer()
    pre_salvage_value = fields.Float()
    reference_note = fields.Char()
    under_warranty = fields.Boolean(string="Warranty Included")
    warranty_period_type = fields.Selection(string="Period",
                                            selection=[('days', 'Days'), ('months', 'Months'),
                                                       ('years', 'Year')], default="days")
    warranty_period = fields.Integer()
    warranty_end_date = fields.Date(string="Warranty Upto", compute="_compute_warranty_end_date")
    under_insurance = fields.Boolean(string="Has Insurance")
    insurance_name_id = fields.Many2one(comodel_name='asset.asset.insurance', string="Type")
    insurance_number = fields.Char(string="ID")
    insurance_start_date = fields.Date(string="Start date")
    insurance_end_date = fields.Date(string="End date")
    has_insurance = fields.Boolean(default=False, compute="_compute_has_insurance")
    reimburse_after_invoice = fields.Boolean(string="Reimburse After Invoice",
                                             help="Enable if insurance reimbursement happens after invoice creation.")
    warranty_attachment_ids = fields.Many2many('ir.attachment', 'asset_warranty_attachment_rel',
                                               'asset_id', 'attachment_id', string="Warranty Documents",
                                               domain="[('res_model', '=', 'asset.asset')]")
    insurance_attachment_ids = fields.Many2many('ir.attachment', 'asset_insurance_attachment_rel',
                                                'asset_id', 'attachment_id', string="Insurance Documents",
                                                domain="[('res_model', '=', 'asset.asset')]")
    buffer_days = fields.Integer(string="Cool Down Days", default=0,
                                 help="Number of days the asset remains unavailable after a booking ends")

    def _compute_maintenance_state(self):
        """Compute maintenance states of assets"""
        for rec in self:
            if rec.is_repair:
                rec.maintenance_state = 'repair'
            elif rec.is_maintenance:
                rec.maintenance_state = 'maintenance'
            else:
                rec.maintenance_state = False

    @api.depends('modified_asset_ids')
    def _compute_modified_count(self):
        """Compute linked modified assets"""
        for rec in self:
            rec.modified_count = len(rec.modified_asset_ids)

    @api.depends('depreciated_entry_ids')
    def _compute_entry_count(self):
        """Compute entries count"""
        self.entry_count = len(self.depreciated_entry_ids)

    @api.depends('name')
    def _compute_maintenance_count(self):
        """Check count of asset repair and maintenance and its current stage"""
        for rec in self:
            maintenance = self.env['maintenance.request'].search([('asset_id', '=', rec.id)])
            rec.maintenance_count = len(maintenance)
            for record in maintenance:
                if record.stage_done == False:
                    if record.maintenance_type == 'corrective':
                        rec.is_repair = True
                    elif record.maintenance_type == 'preventive':
                        rec.is_maintenance = True

    @api.constrains('original_value')
    def _check_original_value(self):
        """Check original value"""
        if self.original_value and self.original_value <= 0:
            self.original_value = abs(self.original_value)
        elif self.original_value and self.salvage_value and round(self.salvage_value, 2) > round(self.original_value,
                                                                                                 2):
            raise UserError(_('The Salvage Value should not be Greater than the Original Value.'))

    @api.constrains('warranty_period')
    def _check_original_value(self):
        """Check warranty period positive number"""
        if self.warranty_period < 0:
            raise UserError(_('The Warranty period should not be a negative Value.'))

    @api.onchange('asset_item_id')
    def _onchange_asset_item_id(self):
        """for getting asset model value of computation method"""
        for record in self:
            record.computation_method = record.asset_item_id.computation_method
            record.depreciation_method = record.asset_item_id.depreciation_method
            record.method_duration = record.asset_item_id.method_duration

    @api.onchange('method_duration')
    def _onchange_method_duration(self):
        """Change methods duration"""
        if self.method_duration < 0:
            self.method_duration = abs(self.method_duration)

    @api.onchange('depreciating_factor')
    def _onchange_depreciating_factor(self):
        """Change depreciating factor"""
        if self.depreciating_factor and self.depreciating_factor < 0:
            self.depreciating_factor = abs(self.depreciating_factor)

    @api.onchange('depreciation_date')
    def _onchange_depreciation_date(self):
        """Change depreciating date"""
        purchase_date = self.date
        if self.depreciation_date and purchase_date and self.depreciation_date < purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The Depreciation Date should be greater than the Purchase Date'))

    @api.onchange('prorata_date')
    def _onchange_prorata_date(self):
        """Change prorata date"""
        purchase_date = self.date
        if self.prorata_date and purchase_date and self.prorata_date < purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The Prorata Date should be greater than the Purchase Date'))

    @api.onchange('insurance_start_date')
    def _onchange_insurance_start_date(self):
        """Function for checking the insurance start date"""
        if self.insurance_start_date and self.insurance_start_date < self.date:
            raise UserError(
                _(f'The Asset is Purchased on {self.date}. The insurance start date should be greater than the Purchase Date'))

    @api.onchange('salvage_value')
    def _onchange_salvage_value(self):
        """Change salvage value"""
        if self.salvage_value:
            if self.salvage_value < 0:
                self.salvage_value = abs(self.salvage_value)
            elif round(self.salvage_value, 2) > round(self.original_value, 2):
                raise UserError(_('The Salvage Value should not be Greater than the Original Value.'))

    @api.onchange('day_amount', 'week_amount', 'month_amount', 'year_amount')
    def _onchange_day_amount(self):
        """Change day amount"""
        if (self.day_amount and self.day_amount <= 0) or (self.month_amount and self.month_amount <= 0) or (
                self.week_amount and self.week_amount <= 0) or (self.year_amount and self.year_amount <= 0):
            raise UserError(_('The value for the rental amount should be an Integer'))

    @api.onchange('fixed_asset_account_id')
    def _onchange_fixed_asset_account_id(self):
        """Function for setting the depreciation account based on fixed asset account"""
        self.asset_depreciation_account_id = self.fixed_asset_account_id

    @api.onchange('asset_expense_account_id')
    def _onchange_asset_expense_account_id(self):
        """Function for setting the loss account based on expense account"""
        self.asset_loss_account_id = self.asset_expense_account_id

    def unlink(self):
        """Function for the unlink the asset"""
        for rec in self:
            if rec.status == 'running':
                raise UserError(_('You cannot delete the record that is in Running state.'))
            elif rec.is_assign or rec.is_lease or rec.is_rental or rec.is_repair or rec.is_maintenance or rec.is_reserve:
                raise UserError(_('You cannot delete the record, The related asset is already taken for some '
                                  'operations'))
            else:
                return super().unlink()

    def action_request_assets(self):
        """Action request assets"""
        states = ['sell', 'disposed', 'cancel']
        if self.status in states:
            asset_state = self.status
            raise UserError(_(
                f'The asset is in {asset_state}.'))
        else:
            return {
                'name': _('Request'),
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                'target': 'new'
            }

    def action_reserve_assets(self):
        """Action reserve assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_reserve or self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            return {
                'name': _('Reservation'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_reservation_form2').id,
                'res_model': 'asset.reservation',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }

    def action_assign_assets(self):
        """Action assign assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Assign'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_assign_form2').id,
                'res_model': 'asset.assign',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_employee_id': reserved_asset.employee_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_lease_assets(self):
        """Action lease assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if not self.is_lease_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a lease asset.'))
        elif self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_repair or self.is_rental:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Lease'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_lease_form2').id,
                'res_model': 'asset.lease',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_customer_id': reserved_asset.employee_id.work_contact_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_rent_assets(self):
        """Action rent assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if not self.is_rental_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a rental asset.'))
        elif self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_assign or self.is_lease or self.is_rental:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.id), ('status', '=', 'reserve')])
            return {
                'name': _('Rental'),
                'view_mode': 'form',
                'view_id': self.env.ref('cyllo_asset_management.view_asset_rental_form2').id,
                'res_model': 'asset.rental',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                    'default_customer_id': reserved_asset.employee_id.work_contact_id.id if reserved_asset else '',
                },
                'target': 'new'
            }

    def action_maintenance_repair_assets(self):
        """Action repair or maintenance assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'leased']
        if self.status in states:
            raise UserError(
                _(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            return {
                'name': _('Maintenance/Repair'),
                'view_mode': 'form',
                'res_model': 'maintenance.request',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }

    def action_lost_missing_assets(self):
        """Action lost missing assets"""
        states = ['sell', 'disposed', 'damaged', 'cancel', 'lost', 'rented', 'reserved', 'leased']
        if self.status in states:
            raise UserError(_(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.depreciated_entry_ids.filtered(lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        elif self.is_entry:
            draft_entry = self.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft')
            if not draft_entry:
                posted = True
            else:
                posted = False
            return {
                'name': _('Lost'),
                'view_mode': 'form',
                'res_model': 'asset.sell.dispose',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_asset_action': 'dispose',
                    'default_disposal_type': 'lost'
                },
                'target': 'new'
            }
        else:
            self.status = 'lost'

    def action_sell_dispose_assets(self):
        """Action sell dispose assets"""
        states = ['sell', 'disposed', 'cancel', 'rented', 'assigned', 'reserved', 'leased']
        if self.status in states:
            raise UserError(_(f'You cannot complete this operation, The related asset is already {self.status}.'))
        elif self.depreciated_entry_ids.filtered(lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        elif self.is_repair or self.is_maintenance:
            raise UserError(_('You cannot complete this operation, The related asset is already taken for a another '
                              'operation'))
        else:
            draft_entry = self.depreciated_entry_ids.filtered(
                lambda e: e.state == 'draft')
            if not draft_entry:
                posted = True
            else:
                posted = False
            return {
                'name': _('Sell/Dispose'),
                'view_mode': 'form',
                'res_model': 'asset.sell.dispose',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_is_posted': posted
                },
                'target': 'new'
            }

    def action_view_reservation(self):
        """Action view reservation"""
        reserved_asset = self.env['asset.reservation'].search([('asset_id', '=', self.id),
                                                               ('status', 'not in', ['draft', 'cancel'])])
        return {
            'name': 'Reservation',
            'view_mode': 'form',
            'res_id': reserved_asset.id,
            'res_model': 'asset.reservation',
            'type': 'ir.actions.act_window',
        }

    def action_view_lease(self):
        """Action view lease"""
        leased_asset = self.env['asset.lease'].search([('asset_id', '=', self.id), ('status', '=', 'lease')])
        return {
            'name': 'Lease',
            'view_mode': 'form',
            'res_model': 'asset.lease',
            'res_id': leased_asset.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_view_rental(self):
        """Action view rental"""
        rental_asset = self.env['asset.rental'].search([('asset_id', '=', self.id), ('status', '=', 'rent')])
        return {
            'name': 'Rental',
            'view_mode': 'form',
            'res_id': rental_asset.id,
            'res_model': 'asset.rental',
            'type': 'ir.actions.act_window',
        }

    def action_view_maintenance_repairs(self):
        """Action view maintenance / repair"""
        return {
            'name': _('Maintenance / Repair'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'default_asset_id': self.id,
                'search_default_asset_id': 1,
            }
        }

    def action_view_assign(self):
        """Action view assign"""
        assigned_asset = self.env['asset.assign'].search([('asset_id', '=', self.id), ('status', '=', 'assign')])
        return {
            'name': 'Assign',
            'view_mode': 'form',
            'res_id': assigned_asset.id,
            'res_model': 'asset.assign',
            'type': 'ir.actions.act_window',
            'domain': [('asset_id', '=', self.id), ('status', '=', 'assign')]
        }

    def action_view_journal_entries(self):
        """Action view journal entries"""
        return {
            'name': 'Journal Entries',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('asset_asset_id', '=', self.id)]
        }

    def action_compute_depreciation(self):
        """Action compute depreciation"""
        self.depreciation_line_ids = [fields.Command.clear()]
        if self.original_value == 0:
            self.is_depreciate = False
            self.salvage_value = self.original_value
            return self
        self.pre_salvage_value = self.salvage_value
        if not self.depreciating_factor:
            self.is_auto_calculate = True
        if self.salvage_value == 0:
            self.salvage_value = self.original_value
        start_fiscal_year = self.company_id.compute_fiscalyear_dates(self.depreciation_date).get('date_from')
        depreciation_date = start_fiscal_year if self.computation_method == 'no_prorata' else self.prorata_date
        calculate_value = abs(self.salvage_value)
        depreciation_duration = 0
        start_date = depreciation_date.replace(day=1)
        if self.duration_period == 'year':
            end_date = start_date + relativedelta(years=self.method_duration)
            total_depreciation_days = (end_date - start_date).days
        else:
            end_date = start_date + relativedelta(months=self.method_duration)
            total_depreciation_days = (end_date - start_date).days
        self.calculate_depreciation(calculate_value, depreciation_duration, depreciation_date, total_depreciation_days)

    def action_confirm_deprecation(self):
        """Button action for the depreciating the asset"""
        if self.original_value == 0:
            raise UserError(_('The Original Value should be Greater than 0.'))
        if self.method_duration == 0:
            raise UserError(_('The duration should be greater than zero.'))
        self.action_compute_depreciation()
        self._create_journal_entries()
        self.status = 'running'
        self.is_confirm = True

    def action_cancel_asset(self):
        """Button action for the cancelling the asset"""
        if self.is_reserve or self.is_assign or self.is_lease or self.is_rental or self.is_repair or self.is_maintenance:
            return {
                'name': 'Assets Cancel warning',
                'view_mode': 'form',
                'res_model': 'asset.cancel.warning',
                'type': 'ir.actions.act_window',
                'context': {
                    'default_asset_id': self.id,
                },
                'target': 'new'
            }
        elif self.depreciated_entry_ids:
            self.depreciated_entry_ids.filtered(lambda d: d.state == 'draft').unlink()
            self.status = 'cancel'
        else:
            self.status = 'cancel'

    def action_modify_asset(self):
        """Button action for the modifying the asset"""
        self.is_revaluate = False
        if self.depreciated_entry_ids.filtered(lambda x: x.state == 'posted' and x.date > Date.today()):
            raise UserError(
                _('Reverse the depreciation entries posted in the future in order to modify the depreciation.'))
        else:
            return {
                'name': _('Modify Asset'),
                'view_mode': 'form',
                'res_model': 'asset.modify',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_asset_asset_id': self.id,
                    'default_asset_journal_id': self.asset_journal_id.id,
                    'default_fixed_asset_account_id': self.fixed_asset_account_id.id,
                    'default_asset_depreciation_account_id': self.asset_depreciation_account_id.id,
                    'default_asset_expense_account_id': self.asset_expense_account_id.id,
                    'default_salvage_value': self.salvage_value,
                    'default_depreciation_method': self.depreciation_method,
                    'default_duration_period': self.duration_period,
                    'default_method_duration': self.method_duration,
                    'default_depreciation_date': self.depreciation_date,
                }
            }

    def action_revaluate_asset(self):
        """Button action for the revaluating the asset"""
        previous_salvage = sum(self.depreciation_line_ids.mapped('depreciation_expense'))
        if self.salvage_value > previous_salvage:
            self.depreciation_line_ids.unlink()
            self.depreciated_entry_ids.unlink()
            self.action_compute_depreciation()
            self._create_journal_entries()
        amount = 0
        previous_amount = 0
        salvage_value = 0
        modify_date = Date.today()
        depreciation_date = modify_date + relativedelta(days=1)
        posted_entries = self.depreciated_entry_ids.filtered(
            lambda e: e.state == 'posted' and not e.reversal_move_id and not e.reversed_entry_id)
        unposted_entries = self.depreciated_entry_ids.filtered(
            lambda e: e.state == 'draft')
        unposted_entries_amount = math.ceil(sum(unposted_entries.mapped('amount_total_signed')))
        if self.duration_period == 'month':
            start_date = modify_date.replace(day=1) if self.computation_method == 'no_prorata' else self.prorata_date
            end_date = end_of(modify_date, granularity='month')
            current_depreciation_entry = (self.depreciated_entry_ids.filtered
                                          (lambda d: d.date.month == modify_date.month
                                                     and d.date.year == modify_date.year
                                                     and d.date != modify_date and d.date == end_date))
            last_date = end_of(depreciation_date, granularity='month')
            days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
            depreciated_days = (modify_date - start_date).days + 1
            depreciating_line = self.depreciation_line_ids.filtered(lambda l: l.date.month == modify_date.month
                                                                              and l.date.year == modify_date.year)
        else:
            start_fiscal_year = self.company_id.compute_fiscalyear_dates(self.depreciation_date).get('date_from')
            start_date = start_fiscal_year if self.computation_method == 'no_prorata' else self.prorata_date
            end_date = end_of(modify_date, granularity='year')
            current_depreciation_entry = self.depreciated_entry_ids.filtered(
                lambda d: d.date.year == modify_date.year and d.date == end_date)
            last_date = end_of(depreciation_date, granularity='year')
            days = 366 if calendar.isleap(depreciation_date.year) else 365
            depreciated_days = (depreciation_date - start_date).days + 1
            depreciating_line = self.depreciation_line_ids.filtered(
                lambda l: l.date.year == modify_date.year and l.date == end_date)
        if not self.is_revaluate and current_depreciation_entry:
            self.is_revaluate = True
            if self.depreciation_method == 'straight_line':
                day_amount = current_depreciation_entry.amount_total_signed / days
            else:
                depreciating_factor = self._get_depreciating_factor(self.salvage_value)
                day_amount = (current_depreciation_entry.amount_total_signed * depreciating_factor / 12) / days
            depreciated_amount = round(depreciated_days * day_amount, 2)
            undepreciated_amount = round(current_depreciation_entry.amount_total_signed - depreciated_amount, 2)
            last_depreciation_date = self.depreciated_entry_ids.filtered(
                lambda record: record.id == max(self.depreciated_entry_ids.ids)).date
            total_depreciation_days = (last_depreciation_date - depreciation_date).days + 1
            self.total_depreciation_days = total_depreciation_days
            duration = self.method_duration - len(posted_entries)
            depreciation_duration = (self.method_duration - duration) + 1 if posted_entries else 0
            self.depreciation_duration = depreciation_duration
            if current_depreciation_entry.state == 'posted':
                amount = -undepreciated_amount
                previous_amount = sum(posted_entries.mapped('amount_total_signed')) - abs(amount)
                salvage_value = unposted_entries_amount - int(amount)

            elif current_depreciation_entry.state == 'draft':
                amount = depreciated_amount
                posted_depreciate_amount = posted_entries.filtered(
                    lambda l: l.id != current_depreciation_entry.id).mapped(
                    'amount_total_signed')
                previous_amount = sum(posted_depreciate_amount) + amount
                salvage_value = unposted_entries_amount - amount

            calculate_value = self.salvage_value - sum(
                unposted_entries.mapped(
                    'amount_total_signed')) if posted_entries or self.pre_salvage_value != self.salvage_value else self.salvage_value if self.pre_salvage_value == self.salvage_value else 0
            modify_vals = []
            if self.salvage_value > previous_salvage:
                if depreciated_amount:
                    modify_vals.append({
                        'depreciation_expense': amount,
                        'depreciation_id': self.id,
                        'date': modify_date,
                        'accumulative_depreciation': previous_amount,
                        'salvage_value': salvage_value,
                    })
                    depreciating_line.unlink() if not depreciating_line.journal_reference else False
                amount = undepreciated_amount
                previous_amount = round(previous_amount + amount, 2)
                salvage_value = round(salvage_value - amount, 2)
                modify_vals.append({
                    'depreciation_expense': amount,
                    'depreciation_id': self.id,
                    'date': last_date,
                    'accumulative_depreciation': previous_amount,
                    'salvage_value': salvage_value,
                })
                for depreciation in modify_vals:
                    line = self.env['asset.depreciation.line'].create(depreciation)
                    self.depreciation_line_ids = [fields.Command.link(line.id)]
                    move_lines = []
                    move_lines.append({
                        'name': self.name,
                        'account_id': self.asset_depreciation_account_id.id,
                        'credit': 0.0 if depreciation['date'] == modify_date else int(
                            depreciation['depreciation_expense']),
                        'debit': int(depreciation['depreciation_expense']) if depreciation[
                                                                                  'date'] == modify_date else 0.0,
                        'currency_id': self.currency_id.id,
                    })
                    move_lines.append({
                        'name': self.name,
                        'account_id': self.asset_expense_account_id.id,
                        'debit': 0.0 if depreciation['date'] == modify_date else int(
                            depreciation['depreciation_expense']),
                        'credit': int(depreciation['depreciation_expense']) if depreciation[
                                                                                   'date'] == modify_date else 0.0,
                        'currency_id': self.currency_id.id,
                    })
                    vals = {
                        'move_type': 'entry',
                        'asset_asset_id': self.id,
                        'ref': _("%s: Depreciation", self.name),
                        'date': depreciation['date'],
                        'invoice_date_due': depreciation['date'],
                        'journal_id': self.asset_journal_id.id,
                        'auto_post': 'at_date',
                        'currency_id': self.currency_id.id,
                        'depreciation_line_id': line.id,
                        'reversed_entry_id': current_depreciation_entry.id if depreciation[
                                                                                  'date'] == modify_date else False,
                        'line_ids': [fields.Command.create(lines) for lines in move_lines],
                    }
                    journal_items = self.depreciated_entry_ids.create(vals)
                    past_journals = journal_items.filtered(lambda x: x.invoice_date_due <= modify_date)
                    if past_journals:
                        past_journals._post()
                self.create_modify_asset(calculate_value, depreciation_duration, depreciation_date,
                                         total_depreciation_days)
                current_depreciation_entry.unlink()
            elif self.salvage_value < unposted_entries_amount:
                self.is_decrease_value = True
                unposted_entries.unlink()
                self.depreciation_line_ids.filtered(lambda l: not l.journal_reference).unlink()
                if depreciated_amount:
                    modify_vals.append({
                        'depreciation_expense': depreciated_amount,
                        'depreciation_id': self.id,
                        'date': modify_date,
                        'accumulative_depreciation': previous_amount,
                        'salvage_value': salvage_value,
                        'is_depreciated': True
                    })
                amount = unposted_entries_amount - self.salvage_value
                previous_amount = round(previous_amount + amount, 2)
                salvage_value = round(salvage_value - amount, 2)
                modify_vals.append({
                    'depreciation_expense': amount,
                    'depreciation_id': self.id,
                    'date': modify_date,
                    'accumulative_depreciation': previous_amount,
                    'salvage_value': salvage_value,
                    'is_depreciated': True
                })
                calculate_value = unposted_entries_amount - amount if posted_entries else self.salvage_value
                calculate_value -= depreciated_amount
                self.depreciation_line_ids = [fields.Command.create(vals) for vals in modify_vals]
                self.calculate_depreciation(int(calculate_value), depreciation_duration, depreciation_date,
                                            total_depreciation_days)
                self._create_journal_entries()


        else:
            posted_value = sum(
                self.depreciated_entry_ids.filtered(lambda a: a.state == 'draft').mapped('amount_total_signed'))
            calculate_value = self.salvage_value - posted_value
            self.modify_value += calculate_value
            depreciation_duration = self.depreciation_duration
            total_depreciation_days = self.total_depreciation_days
            self.create_modify_asset(calculate_value, depreciation_duration, depreciation_date, total_depreciation_days)
        self.is_modify = False
        self.is_confirm = True

    def action_reset_to_draft(self):
        """Button action for the reset the asset in to the draft state"""
        self.salvage_value = self.original_value
        if self.depreciated_entry_ids:
            self.depreciated_entry_ids.filtered(lambda e: e.state in ('posted', 'cancel')).button_draft()
            self.depreciated_entry_ids.filtered(lambda d: d.state == 'draft').unlink()
        if self.modified_asset_ids:
            self.modified_asset_ids.unlink()
        self.depreciation_line_ids.unlink()
        self.status = 'draft'
        self.is_depreciate = False
        self.is_entry = False
        self.is_modify = False
        self.is_confirm = False
        self.is_reserve = False
        self.is_assign = False
        self.is_lease = False
        self.is_rental = False
        self.is_repair = False
        self.is_maintenance = False
        self.is_sell = False
        self.is_dispose = False
        self.is_lost = False
        self.modify_value = 0
        self.is_revaluate = False
        self.is_decrease_value = False

    def action_view_modified_asset(self):
        """Function for the viewing the modified asset"""
        return {
            'name': 'Asset',
            'view_mode': 'tree,form',
            'res_model': 'asset.asset',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.modified_asset_ids.ids)]
        }

    def _get_depreciating_factor(self, calculate_value):
        """Depreciating factor"""
        depreciating_factor = 0
        if self.is_auto_calculate:
            declining_factor = round(calculate_value / self.method_duration, 2)
            double_factor = round(declining_factor / calculate_value, 2)
            if self.depreciation_method in ['declining_balance', 'declining_straight_line']:
                depreciating_factor = round(double_factor, 2)
            elif self.depreciation_method == 'double_declining':
                depreciating_factor = round(double_factor * 2, 2)
        else:
            if self.depreciation_method in ['declining_balance', 'declining_straight_line']:
                depreciating_factor = self.depreciating_factor
            elif self.depreciation_method == 'double_declining':
                depreciating_factor = self.depreciating_factor * 2
        return depreciating_factor

    def _compute_no_prorata_depreciation_amount(self, calculate_value, salvage_value, year, depreciating_factor,
                                                depreciation_days, balancing_value, depreciate_value):
        """Compute no prorata depreciation amount"""
        if self.depreciation_method == 'straight_line':
            amount = calculate_value / self.method_duration
            if year == self.method_duration:
                amount = salvage_value
        elif self.depreciation_method == 'declining_straight_line':
            if self.duration_period == 'month':
                amount = calculate_value / self.method_duration
            else:
                if year == 1:
                    amount = depreciating_factor * calculate_value
                elif year == self.method_duration:
                    amount = salvage_value
                else:
                    amount = salvage_value * depreciating_factor
        else:
            depreciate_amount = round(depreciate_value / 12, 2)
            if year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                amount = depreciating_factor * salvage_value if self.duration_period == 'year' else depreciate_amount
        return amount

    def _compute_constant_period_depreciation_amount(self, calculate_value, salvage_value, year, depreciation_date,
                                                     balance_month, balancing_value, depreciate_value,
                                                     depreciating_factor, total_depreciation_days, depreciation_days,
                                                     depreciation_duration):
        """Compute constant period depreciation amount"""
        day_count = 366 if calendar.isleap(depreciation_date.year) else 365
        if self.depreciation_method == 'straight_line':
            if not self.is_revaluate:
                straight_line_value = calculate_value / self.method_duration
                depreciation_days = (30 - depreciation_date.day) + 1
                if year == 1:
                    year_amount = straight_line_value
                    month_amount = round(year_amount / 12, 2)
                    day_amount = round(month_amount / 30, 2)
                    current_month_depreciation = round(depreciation_days * day_amount, 2)
                    amount = ((
                                      balance_month * month_amount) + current_month_depreciation) if self.duration_period == 'year' else round(
                        (year_amount / 30) * depreciation_days, 2)
                elif year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = straight_line_value
            else:
                day_value = calculate_value / total_depreciation_days
                amount = day_value * depreciation_days

        elif self.depreciation_method == 'declining_straight_line':
            if not self.is_revaluate:
                if self.duration_period == 'month':
                    amount = calculate_value / self.method_duration
                else:
                    if year == 1:
                        day_amount = depreciate_value / day_count
                        amount = day_amount * depreciation_days
                    elif year == self.method_duration + balancing_value:
                        amount = salvage_value
                    else:
                        amount = depreciating_factor * salvage_value
            else:
                day_value = calculate_value / total_depreciation_days
                amount = day_value * depreciation_days
        else:
            depreciate_amount = round(depreciate_value / 12, 2)
            if not self.is_revaluate or self.is_decrease_value:
                if year == 1:
                    day_amount = depreciate_value / day_count
                    amount = day_amount * depreciation_days if self.duration_period == 'year' else depreciate_amount
                elif year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = depreciating_factor * salvage_value if self.duration_period == 'year' else depreciate_amount
            else:
                if year == self.method_duration + balancing_value:
                    amount = salvage_value
                else:
                    amount = depreciating_factor * salvage_value
        return amount

    def _compute_daily_compute_depreciation_amount(self, calculate_value, salvage_value, year, year_end_depreciation,
                                                   depreciation_date, total_depreciation_days,
                                                   depreciation_days, balancing_value, depreciating_factor):
        """Compute daily depreciation amount"""
        total_days = (year_end_depreciation - depreciation_date).days + 1
        total_month_days = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
        day_count = 366 if calendar.isleap(depreciation_date.year) else 365
        depreciate_value = depreciating_factor * salvage_value
        year_amount = round(depreciate_value / day_count, 2)

        day_amount = calculate_value / total_depreciation_days
        if self.depreciation_method == 'straight_line':
            if year == 1:
                if self.duration_period == 'year':
                    amount = day_amount * total_days
                else:
                    amount = day_amount * depreciation_days
            elif year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                if self.duration_period == 'year':
                    amount = day_amount * day_count
                else:
                    amount = day_amount * total_month_days
        elif self.depreciation_method == 'declining_straight_line':
            if year == 1:
                if self.duration_period == 'year':
                    amount = year_amount * total_days
                else:
                    amount = day_amount * total_month_days
            elif year == self.method_duration + balancing_value:
                if self.duration_period == 'year':
                    amount = depreciate_value * day_count
                else:
                    amount = day_amount * total_month_days
            else:
                if self.duration_period == 'year':
                    amount = depreciate_value
                else:
                    amount = day_amount * total_month_days
        else:
            if year == 1:
                if self.duration_period == 'year':
                    amount = round(year_amount * total_days, 2)
                else:
                    amount = round(year_amount * depreciation_days, 2)
            elif year == self.method_duration + balancing_value:
                amount = salvage_value
            else:
                if self.duration_period == 'year':
                    amount = salvage_value * depreciating_factor
                else:
                    amount = round(year_amount * total_month_days, 2)
        return amount

    def _create_depreciation_lines(self, calculate_value, amount, year, year_end_depreciation, month_end_depreciation,
                                   previous_amount, salvage_value, depreciating_factor, balancing_value):
        """Creating depreciation lines"""
        depreciate_value = 0
        if self.is_decrease_value:
            previous_amount = math.ceil(self.depreciation_line_ids.filtered(
                lambda record: record.id == max(self.depreciation_line_ids.ids)).accumulative_depreciation + amount)
            salvage_value = self.depreciation_line_ids.filtered(
                lambda record: record.id == max(self.depreciation_line_ids.ids)).salvage_value - amount
            if self.method_duration + balancing_value == year:
                self.is_decrease_value = False
                previous_amount -= amount
                amount = salvage_value + amount
                calculate_value = previous_amount + amount
                calculate_value = calculate_value if calculate_value == self.pre_salvage_value else self.pre_salvage_value
                previous_amount = calculate_value
                salvage_value = 0
        else:
            depreciate_value = depreciating_factor * calculate_value
        vals = [fields.Command.create({
            'depreciation_expense': calculate_value if depreciate_value > calculate_value else amount,
            'depreciation_id': self.id,
            'date': year_end_depreciation if self.duration_period == 'year' else month_end_depreciation,
            'accumulative_depreciation': calculate_value if depreciate_value > calculate_value or previous_amount > calculate_value and not self.is_decrease_value else previous_amount,
            'salvage_value': 0 if depreciate_value > calculate_value or previous_amount > calculate_value and not self.is_decrease_value else
            salvage_value,
        })]
        self.write({'depreciation_line_ids': vals})

    def _create_journal_entries(self):
        """Create journal entries"""
        for depreciation in self.depreciation_line_ids:
            if not depreciation.journal_reference:
                move_lines = []
                move_lines.append({
                    'name': self.name,
                    'account_id': self.asset_depreciation_account_id.id,
                    'credit': depreciation.depreciation_expense,
                    'debit': 0.0,
                    'currency_id': self.currency_id.id,
                })
                move_lines.append({
                    'name': self.name,
                    'account_id': self.asset_expense_account_id.id,
                    'debit': depreciation.depreciation_expense,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                })
                vals = {
                    'move_type': 'entry',
                    'asset_asset_id': self.id,
                    'ref': _("%s: Depreciation", self.name),
                    'date': depreciation.date,
                    'invoice_date_due': depreciation.date,
                    'journal_id': self.asset_journal_id.id,
                    'auto_post': 'at_date',
                    'depreciation_line_id': depreciation.id,
                    'line_ids': [fields.Command.create(lines) for lines in move_lines],
                }
                journal_items = self.env['account.move'].create(vals)
                past_journals = journal_items.filtered(lambda x: x.invoice_date_due <= fields.date.today())

                if past_journals:
                    past_journals._post()

    def calculate_depreciation(self, calculate_value, depreciation_duration, depreciation_date,
                               total_depreciation_days):
        """Calculation depreciation values"""
        self.is_depreciate = True
        self.is_entry = True
        depreciating_factor = self._get_depreciating_factor(calculate_value)
        depreciate_value = calculate_value * depreciating_factor
        year_end_depreciation = self.company_id.compute_fiscalyear_dates(depreciation_date).get('date_to')
        month_end_depreciation = end_of(depreciation_date, granularity='month')
        if self.duration_period == 'month':
            depreciation_days = (month_end_depreciation - depreciation_date).days + 1
        else:
            depreciation_days = (year_end_depreciation - depreciation_date).days + 1
        balance_month = year_end_depreciation.month - depreciation_date.month
        straight_line_value = calculate_value / self.method_duration
        salvage_value = calculate_value
        previous_amount = 0
        balancing_value = 0 if self.computation_method == 'no_prorata' else 1
        for period in range(self.method_duration + balancing_value):
            year = period + 1
            if year >= depreciation_duration:
                amount = 0
                if self.computation_method == 'no_prorata':
                    amount = self._compute_no_prorata_depreciation_amount(calculate_value, salvage_value, year,
                                                                          depreciating_factor, depreciation_days,
                                                                          balancing_value, depreciate_value)
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value:
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount, salvage_value, calculate_value,
                                                                year_end_depreciation, month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = salvage_value - amount if year > 1 else calculate_value - amount

                if self.computation_method == 'constant_period':
                    amount = self._compute_constant_period_depreciation_amount(calculate_value, salvage_value, year,
                                                                               depreciation_date,
                                                                               balance_month, balancing_value,
                                                                               depreciate_value,
                                                                               depreciating_factor,
                                                                               total_depreciation_days,
                                                                               depreciation_days, depreciation_duration)
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value:
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount, salvage_value,
                                                                calculate_value,
                                                                year_end_depreciation, month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = salvage_value - amount if year > 1 else calculate_value - amount
                if self.computation_method == 'daily_compute':
                    amount = self._compute_daily_compute_depreciation_amount(calculate_value, salvage_value, year,
                                                                             year_end_depreciation,
                                                                             depreciation_date, total_depreciation_days,
                                                                             depreciation_days, balancing_value,
                                                                             depreciating_factor)
                    if self.depreciation_method == 'declining_straight_line' and amount <= straight_line_value and self.duration_period == 'year':
                        amount = straight_line_value
                        self._calculate_declining_straight_line(amount, previous_amount, salvage_value,
                                                                calculate_value,
                                                                year_end_depreciation, month_end_depreciation,
                                                                year, balancing_value)
                        break
                    previous_amount = amount if year == 1 else previous_amount + amount
                    salvage_value = calculate_value - amount if year == 1 else salvage_value - amount
                self._create_depreciation_lines(calculate_value, amount, year, year_end_depreciation,
                                                month_end_depreciation, previous_amount, salvage_value,
                                                depreciating_factor, balancing_value)

                if (depreciating_factor * calculate_value > calculate_value) or (
                        round(previous_amount, 2) >= calculate_value):
                    break
                if self.duration_period == 'month':
                    depreciation_date = month_end_depreciation + relativedelta(months=1)
                    month_end_depreciation = end_of(depreciation_date, granularity='month')
                    depreciation_days = 30 if self.computation_method == 'constant_period' else \
                        calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                else:
                    depreciation_date = year_end_depreciation + relativedelta(years=1)
                    year_end_depreciation = end_of(depreciation_date, granularity='year')
                    depreciation_days = 366 if calendar.isleap(depreciation_date.year) else 365

    def _calculate_declining_straight_line(self, amount, previous_amount, salvage_value, calculate_value,
                                           year_end_depreciation, month_end_depreciation,
                                           year, balancing_value):
        """Calculation depreciation values for declining straight line method"""
        year_count = (self.method_duration + balancing_value) - (year - 1) if year > 1 else (
                self.method_duration + balancing_value)
        for count in range(year_count):
            vals = [fields.Command.create({
                'depreciation_expense': salvage_value if salvage_value < amount else amount,
                'depreciation_id': self.id,
                'year': year,
                'date': year_end_depreciation if self.duration_period == 'year' else month_end_depreciation,
                'accumulative_depreciation': previous_amount + salvage_value if salvage_value < amount else previous_amount + amount,
                'salvage_value': salvage_value - amount if salvage_value > amount else 0,
            })]

            if self.duration_period == 'month':
                depreciation_date = month_end_depreciation + relativedelta(months=1)
                month_end_depreciation = end_of(depreciation_date, granularity='month')

            else:
                depreciation_date = year_end_depreciation + relativedelta(years=1)
                year_end_depreciation = end_of(depreciation_date, granularity='year')

            self.write({'depreciation_line_ids': vals})
            year = year + 1
            previous_amount = previous_amount + amount
            salvage_value = salvage_value - amount
            if (amount > calculate_value) or (round(previous_amount, 2) >= calculate_value):
                break

    def create_modify_asset(self, calculate_value, depreciation_duration, depreciation_date, total_depreciation_days):
        """Function for creating modified asset"""
        self.modify_value = abs(calculate_value)
        if self.modify_value < 0:
            raise UserError(
                _('You cannot create an asset from lines containing credit and debit on the account or with a null amount'))
        vals = {
            'name': _("%s: %s", self.reference_note, self.name),
            'parent_id': self.id,
            'method_duration': self.method_duration,
            'duration_period': self.duration_period,
            'asset_item_id': self.asset_item_id.id,
            'asset_journal_id': self.asset_journal_id.id,
            'fixed_asset_account_id': self.fixed_asset_account_id.id,
            'asset_depreciation_account_id': self.asset_depreciation_account_id.id,
            'asset_expense_account_id': self.asset_expense_account_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'status': 'running',
            'brand_id': self.brand_id,
            'original_value': calculate_value,
            'salvage_value': calculate_value,
            'depreciation_method': self.depreciation_method,
            'depreciation_date': self.depreciation_date,
            'computation_method': 'constant_period',
            'prorata_date': depreciation_date,
            'is_auto_calculate': self.is_auto_calculate if self.is_auto_calculate else False,
            'depreciating_factor': self.depreciating_factor if self.depreciating_factor else False,
        }
        modified_asset = self.env['asset.asset'].sudo().create(vals)
        self.modified_asset_ids = [fields.Command.link(modified_asset.id)]
        modified_asset.is_revaluate = True
        modified_asset.calculate_depreciation(calculate_value, depreciation_duration, depreciation_date,
                                              total_depreciation_days)
        modified_asset._create_journal_entries()
        modified_asset.is_confirm = True
        total_value = sum(
            self.depreciated_entry_ids.filtered(lambda a: a.state == 'draft').mapped('amount_total_signed'))
        total_value += sum(
            self.modified_asset_ids.filtered(lambda a: a.status == 'running').mapped('salvage_value'))
        self.salvage_value = total_value

    @api.depends('warranty_period', 'warranty_period_type')
    def _compute_warranty_end_date(self):
        for record in self:
            if record.warranty_period and record.warranty_period_type:
                if record.warranty_period_type == 'days':
                    record.warranty_end_date = record.date + relativedelta(days=record.warranty_period)
                if record.warranty_period_type == 'months':
                    record.warranty_end_date = record.date + relativedelta(months=record.warranty_period)
                if record.warranty_period_type == 'years':
                    record.warranty_end_date = record.date + relativedelta(years=record.warranty_period)
            else:
                record.warranty_end_date = fields.Date.today()

    @api.onchange('asset_item_id')
    def _onchange_asset_item(self):
        if self.asset_item_id:
            for record in self:
                record.brand_id = record.asset_item_id.brand_id
                record.is_auto_calculate = record.asset_item_id.is_auto_calculate
                record.depreciating_factor = record.asset_item_id.depreciating_factor
                record.duration_period = record.asset_item_id.duration_period
                record.fixed_asset_account_id = record.asset_item_id.fixed_asset_account_id
                record.asset_depreciation_account_id = record.asset_item_id.asset_depreciation_account_id
                record.asset_expense_account_id = record.asset_item_id.asset_expense_account_id
                record.asset_loss_account_id = record.asset_item_id.asset_loss_account_id
                record.asset_journal_id = record.asset_item_id.asset_journal_id
                record.prorata_date = record.asset_item_id.prorata_date
                record.vendor_id = record.asset_item_id.vendor_id
