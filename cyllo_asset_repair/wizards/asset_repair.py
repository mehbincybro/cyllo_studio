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


class AssetRepair(models.TransientModel):
    """ Wizard model for asset repair"""
    _name = 'asset.repair'
    _description = 'Asset Repair'

    def get_repair_user(self):
        repair_user = self.env.ref('cyllo_asset_repair.group_cyllo_asset_repair')
        return [('id', 'in', repair_user.users.ids)]

    asset_id = fields.Many2one('asset.asset', string='Asset ID', required=True)
    issue = fields.Text(required=True)
    user_id = fields.Many2one('res.users', string='Responsible User', domain=get_repair_user)
    employee_id = fields.Many2one('hr.employee', required=True)
    scheduled_date = fields.Date(required=True)

    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        """Function for checking the schedduled date"""
        purchase_date = self.asset_id.date
        if self.scheduled_date and self.scheduled_date <= purchase_date:
            raise UserError(
                _(f'The Asset is Purchased on {purchase_date}.The schedule Date should be greater than the Purchase Date'))

    def action_send_repair(self):
        """Button action for create repair request"""
        self.asset_id.is_repair = True
        date = fields.Date.today()
        self.env['account.asset.repair'].create({
            'asset_id': self.asset_id.id,
            'issue': self.issue,
            'employee_id': self.employee_id.id,
            'department_id': self.employee_id.department_id.id,
            'user_id': self.user_id.id,
            'date': date,
            'asset_item_id': self.asset_id.asset_item_id.id,
            'asset_type_id': self.asset_id.asset_type_id.id,
            'scheduled_date': self.scheduled_date
        })
