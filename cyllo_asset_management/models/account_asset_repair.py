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


class AccountAssetRepair(models.Model):
    """Model for the asset repairing"""
    _name = 'account.asset.repair'
    _description = 'Account Assets Repair'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one('asset.asset', required=True)
    asset_item_id = fields.Many2one('asset.item', related='asset_id.asset_item_id')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    status = fields.Selection(
        [('new', 'New'), ('confirm', 'Confirm'), ('repairing', 'Repairing'), ('repaired', 'Repaired'),
         ('scrap', 'Scrap')], default='new', tracking=True, copy=False)
