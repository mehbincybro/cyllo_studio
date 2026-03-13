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
from odoo import api, fields, models


class CarbonEmissionSource(models.Model):
    _name = 'carbon.source'
    _description = 'Emission Source'
    _order = 'name'

    name = fields.Char(required=True)
    category = fields.Selection([
        ('energy', 'Energy'),
        ('transport', 'Transport'),
        ('materials', 'Materials'),
        ('waste', 'Waste'),
        ('services', 'Services'),
        ('other', 'Other'),
    ], default='other', required=True)
    activity_unit = fields.Many2one('carbon.unit', string='Activity Unit')
    scope_id = fields.Many2one('carbon.scope', ondelete='restrict')
    active = fields.Boolean(default=True)
    description = fields.Text()

    factor_ids = fields.One2many('carbon.factor', 'source_id', string='Factors')

    @api.depends('factor_ids')
    def _compute_factor_count(self):
        for rec in self:
            rec.factor_count = len(rec.factor_ids)

    factor_count = fields.Integer(compute='_compute_factor_count', string='Factor Count')
