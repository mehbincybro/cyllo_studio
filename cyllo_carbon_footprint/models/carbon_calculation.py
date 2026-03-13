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


class CarbonCalculation(models.Model):
    _name = 'carbon.calc'
    _description = 'Carbon Calculation'
    _order = 'date desc, name'

    name = fields.Char(required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    activity_ids = fields.One2many('carbon.activity', 'calculation_id', string='Activities')
    total_emissions = fields.Float(compute='_compute_totals', string='Total Emissions')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', required=True)
    note = fields.Text()

    @api.depends('activity_ids.emission_total')
    def _compute_totals(self):
        for rec in self:
            rec.total_emissions = sum(rec.activity_ids.mapped('emission_total'))

    def action_mark_done(self):
        for rec in self:
            rec.state = 'done'
