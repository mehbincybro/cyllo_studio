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


class AssetScrap(models.Model):
    """Model for the asset scrap"""
    _name = 'asset.scrap'
    _description = 'Account Scrap'
    _inherit = ['mail.thread']
    _rec_name = 'asset_id'

    asset_id = fields.Many2one('asset.asset', required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    status = fields.Selection([('draft', 'Draft'), ('scraped', 'Scraped')], default='draft', copy=False)
    active = fields.Boolean(default=True)

    def create(self, vals_list):
        """Super the create function for checking the conditions"""
        res = super().create(vals_list)
        asset = self.env['asset.asset'].browse(vals_list.get('asset_id'))
        reserved_asset = self.env['asset.reservation'].search(
            [('asset_id', '=', asset.id), ('status', '=', 'reserve')])
        if reserved_asset:
            asset.is_reserve = False
            reserved_asset.unlink()
        assigned_asset = self.env['asset.assign'].search(
            [('asset_id', '=', asset.id), ('status', '=', 'assign')])
        if assigned_asset:
            asset.is_assign = False
            assigned_asset.unlink()
        leased_asset = self.env['asset.lease'].search(
            [('asset_id', '=', asset.id), ('status', '=', 'lease')])
        if leased_asset:
            asset.is_lease = False
            leased_asset.unlink()
        rental_asset = self.env['asset.rental'].search(
            [('asset_id', '=', asset.id), ('status', '=', 'rent')])
        if rental_asset:
            asset.is_rental = False
            rental_asset.unlink()
        return res
