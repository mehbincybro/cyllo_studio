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


class AssetAssign(models.Model):
    """Model for assigning the assets"""
    _name = 'asset.assign'
    _description = 'Assign Assets'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one('asset.asset', required=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    email = fields.Char(related='employee_id.work_email')
    assign_date = fields.Date(required=True, tracking=True)
    reservation_id = fields.Many2one('asset.reservation')
    assign_note = fields.Text(string="Note")
    company_id = fields.Many2one('res.company',
                                 required=True,
                                 default=lambda self: self.env.company,
                                 help='Select the company')
    status = fields.Selection(
        [('draft', 'Draft'), ('assign', 'Assign'), ('cancel', 'Cancel')], default='draft', tracking=True, copy=False)
    active = fields.Boolean(default=True)

    @api.onchange('assign_date')
    def _onchange_assign_date(self):
        """Function for checking the assign date"""
        purchase_date = self.asset_id.asset_item_id.purchase_date
        if self.assign_date and self.assign_date < purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}. The Assign Date should be greater than the Purchase Date'))

    def unlink(self):
        """Function for unlink the assign records"""
        for rec in self:
            if rec.status == 'assign':
                raise UserError(_('You cannot delete the record that is in Assign state.'))
        else:
            self.asset_id.is_assign = False
            return super().unlink()

    def action_assign(self):
        """Button action for assign the asset"""
        if self.asset_id.is_assign:
            raise UserError(_('You cannot complete this operation, The related asset is already Assigned.'))
        repair_asset = self.env['account.asset.repair'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'repairing'])])
        maintenance_asset = self.env['account.asset.maintenance'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'ongoing'])])
        if (maintenance_asset and self.assign_date <= maintenance_asset.scheduled_date) or (
                repair_asset and self.assign_date <= repair_asset.scheduled_date):
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            self.status = 'assign'
            self.asset_id.is_assign = True
            context = {
                'asset': self.asset_id.name,
                'assign_date': self.assign_date,
                'employee': self.employee_id.name
            }
            template = self.env.ref(
                'cyllo_asset_management.mail_template_asset_assignment',
                raise_if_not_found=False)
            email_values = {
                'email_to': self.email
            }
            template.with_context(**context).send_mail(res_id=self.id, email_values=email_values, force_send=True)
            if self.reservation_id:
                self.asset_id.is_reserve = False
                self.reservation_id.write({
                    'status': 'assign'})

    def action_unassign(self):
        """Button action for unassign the asset"""
        self.status = 'cancel'
        self.asset_id.is_assign = False
        asset_id = self.asset_id.id
        reserved_asset = self.env['asset.reservation'].search(
            [('asset_id', '=', asset_id), ('status', '=', 'assign')])
        reserved_asset.write({
            'status': 'cancel'})

    def action_reset_to_draft(self):
        """Button action for reset the record in to draft state"""
        if self.asset_id.status in ('sell', 'disposed', 'cancel', 'lost'):
            raise UserError(_(f'You cannot reset to draft.The related asset is in {self.asset_id.status} state.'))
        self.status = 'draft'
