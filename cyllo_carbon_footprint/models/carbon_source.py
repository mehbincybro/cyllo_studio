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
    air_factor_ids = fields.One2many('carbon.factor', 'source_id',domain=[('type', '=', 'air')], context={'default_type': 'air'}, string="Air Factors")
    sound_factor_ids = fields.One2many('carbon.factor', 'source_id', domain=[('type', '=', 'sound')], context={'default_type': 'sound'}, string="Sound Factors")
    water_factor_ids = fields.One2many('carbon.factor', 'source_id', domain=[('type', '=', 'water')], context={'default_type': 'water'}, string="Water Factors")
    factor_count = fields.Integer(compute='_compute_factor_count', string='Factor Count')

    @api.depends('air_factor_ids', 'sound_factor_ids','water_factor_ids')
    def _compute_factor_count(self):
        for rec in self:
            air_factor_count=len(rec.air_factor_ids)
            sound_factor_count=len(rec.sound_factor_ids)
            water_factor_count=len(rec.water_factor_ids)
            rec.factor_count = air_factor_count+sound_factor_count+water_factor_count


