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
from odoo import fields, models


class AssetCancelWarning(models.TransientModel):
    """Module for the cancel warning"""
    _name = 'asset.cancel.warning'
    _description = 'Asset Cancel Warning'

    asset_id = fields.Many2one('asset.asset')

    def action_asset_unlink(self):
        """Button action for unlink the assets"""
        reserved_asset = self.env['asset.reservation'].search(
            [('asset_id', '=', self.asset_id.id), ('status', '=', 'reserve')])
        if reserved_asset:
            self.asset_id.is_reserve = False
            reserved_asset.unlink()
        assigned_asset = self.env['asset.assign'].search(
            [('asset_id', '=', self.asset_id.id), ('status', '=', 'assign')])
        if assigned_asset:
            self.asset_id.is_assign = False
            assigned_asset.unlink()
        leased_asset = self.env['asset.lease'].search(
            [('asset_id', '=', self.asset_id.id), ('status', '=', 'lease')])
        if leased_asset:
            self.asset_id.is_lease = False
            leased_asset.unlink()
        rental_asset = self.env['asset.rental'].search(
            [('asset_id', '=', self.asset_id.id), ('status', '=', 'rent')])
        if rental_asset:
            self.asset_id.is_rental = False
            rental_asset.unlink()
        repair_asset = self.env['account.asset.repair'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'ongoing'])])
        if repair_asset:
            self.asset_id.is_repair = False
            repair_asset.unlink()
        maintenance_asset = self.env['account.asset.maintenance'].search(
            [('asset_id', '=', self.asset_id.id), ('status', 'in', ['new', 'confirm', 'repairing'])])
        if maintenance_asset:
            self.asset_id.is_maintenance = False
            maintenance_asset.unlink()
        self.asset_id.status = 'cancel'
