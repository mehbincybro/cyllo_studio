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


class AssetDepreciationLine(models.Model):
    """Model for asset depreciation lines"""
    _name = 'asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'date, accumulative_depreciation asc'

    depreciation_id = fields.Many2one('asset.asset')
    year = fields.Integer()
    date = fields.Date()
    is_depreciated = fields.Boolean()
    depreciation_expense = fields.Float()
    accumulative_depreciation = fields.Float(string='Accumulated Depreciation', digits=(12, 6))
    salvage_value = fields.Float(string='Book Value at Year End')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  help='Currency of company')
    journal_reference = fields.Char(string='Journal Entry')
