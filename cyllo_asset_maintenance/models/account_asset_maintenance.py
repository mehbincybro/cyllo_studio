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


class AccountAssetMaintenance(models.Model):
    """Inherit the module for adding new fields"""
    _inherit = 'account.asset.maintenance'

    def get_maintenance_user(self):
        """Function for user domain """
        maintenance_user = self.env.ref('cyllo_asset_maintenance.group_cyllo_asset_maintenance')
        return [('id', 'in', maintenance_user.users.ids)]

    reference = fields.Char(default='New', readonly=True)
    issue = fields.Char(copy=False, required=True)
    asset_type_id = fields.Many2one("asset.type", related='asset_id.asset_type_id')
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True, copy=False)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', copy=False)
    user_id = fields.Many2one('res.users', string='Responsible User', copy=False, domain=get_maintenance_user)
    date = fields.Date(default=fields.Date.context_today, copy=False)
    scheduled_date = fields.Date(copy=False, required=True)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')

    is_scrap = fields.Boolean()
    active = fields.Boolean(default=True)
    under_warranty = fields.Boolean(string="Under Warranty", related='asset_id.under_warranty')
    warranty_percentage = fields.Float(string="Warranty Deduction in %", default=100)

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        """Function for checking scheduled date"""
        purchase_date = self.asset_id.date
        if self.scheduled_date and self.scheduled_date <= purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The schedule Date should be greater than the Purchase Date'))

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Function for updating the user"""
        if self.asset_id.is_reserve:
            reserved_asset = self.env['asset.reservation'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'reserve')])
            self.employee_id = reserved_asset.employee_id.id
        elif self.asset_id.is_lease:
            leased_asset = self.env['asset.lease'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'lease')])
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', leased_asset.customer_id.id)]).id
        elif self.asset_id.is_assign:
            assigned_asset = self.env['asset.assign'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'assign')])
            self.employee_id = assigned_asset.employee_id.id
        elif self.asset_id.is_rental:
            rental_asset = self.env['asset.rental'].search(
                [('asset_id', '=', self.asset_id.id), ('status', '=', 'rent')])
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', rental_asset.customer_id.id)]).id
        else:
            self.employee_id = self.env['hr.employee'].search(
                [('work_contact_id', '=', self.env.user.partner_id.id)]).id

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'account.asset.maintenance') or ''
        return super(AccountAssetMaintenance, self).create(vals)

    def action_confirm(self):
        """Button action for confirming the request"""
        self.status = 'confirm'
        self.asset_id.is_maintenance = True

    def action_start_maintenance(self):
        """Button action for start maintenance"""
        if self.asset_id.is_lease == True or self.asset_id.is_rental == True:
            raise UserError(_("The asset is leased or rented... please return it before you continue"))
        else:
            self.status = 'ongoing'
            self.asset_id.status = 'maintenance'

    def action_done(self):
        """Button action for complete maintenance"""
        self.status = 'done'
        self.asset_id.is_maintenance = False
        if self.asset_id.is_reserve == True:
            self.asset_id.status = 'reserved'
        elif self.asset_id.is_assign == True:
            self.asset_id.status = 'assigned'
        elif self.asset_id.is_confirm == True:
            self.asset_id.status = 'running'
        else:
            self.asset_id.status = 'draft'

    def action_scraped(self):
        """Button action for scrap maintenance asset"""
        self.status = 'scrap'
        self.is_scrap = True
        self.asset_id.is_maintenance = False
        if self.asset_id.is_entry:
            action_scrap = self.env['asset.sell.dispose'].sudo().create({
                'asset_asset_id': self.asset_id.id,
                'asset_action': 'dispose',
                'loss_account_id': self.asset_item_id.asset_loss_account_id.id,
                'date': fields.Date.today(),
                'note': "Scrapped after maintenance",
                'disposal_type': 'scrap',
            })
            action_scrap.action_dispose()
        else:
            self.env['asset.sell.dispose'].sudo().create({
                'asset_asset_id': self.asset_id.id,
                'asset_action': 'dispose',
                'date': fields.Date.today(),
                'note': "Scrapped after maintenance",
                'disposal_type': 'scrap',
            })

    def unlink(self):
        """Function for unlink records"""
        for rec in self:
            if rec.status in ['confirm', 'ongoing']:
                raise UserError(_(f'You cannot delete the record that is in {rec.status} state.'))
            else:
                rec.asset_id.is_maintenance = False
                return super().unlink()
