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
from email.policy import default

from odoo import api,fields, models
import json

class QualityInspection(models.Model):
    _name = 'quality.inspection'
    _description = 'Quality Inspections'
    _order = 'priority'

    priority = fields.Integer(default=1)


    quality_control_id = fields.Many2one('quality.control.point', string='Quality Control Point')
    inspection_action_id = fields.Many2one('inspection.action', string='Actions', required=True)
    name = fields.Char(compute='_compute_name', string='Actions')
    inspection_type_id = fields.Many2one('inspection.type', string='Type')
    blocked_by_id = fields.Many2one('quality.inspection', string='Blocked By', domain="[('quality_control_id', '=', quality_control_id), ('quality_control_id', '!=', False), ('id', '!=', id)]")
    value = fields.Json(default=lambda self: {
        "unit": {
            "id": False,
            "name": ''
        },
        "value": ''
    })
    is_measure = fields.Boolean(compute='_compute_is_measure')
    instruction = fields.Text(string='Quality Check Instructions')
    measure_start = fields.Float(string='Start')
    measure_end = fields.Float(string='End')
    unit_id = fields.Many2one('uom.uom', string='Unit')

    @api.depends('inspection_action_id', 'priority')
    def _compute_name(self):
        for record in self:
            action_name = record.inspection_action_id.name or ''
            record.name = f"{record.priority if record.priority else ''},{action_name} "

    def action_add_instruction(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'quality_instruction_action',
            'target': 'new',
            'params': {
                'res_id': self.id,
            }
        }

    @api.depends('inspection_type_id')
    def _compute_is_measure(self):
        measure_inspection_type_id = self.env.ref('cyllo_quality.inspection_type_measure').id
        for record in self:
            record.is_measure = False
            if record.inspection_type_id.id == measure_inspection_type_id:
                record.is_measure = True


    @api.onchange('inspection_type_id')
    def _onchange_inspection_type_id(self):
        if self.inspection_type_id.name != 'Measure':
            self.measure_start = False
            self.measure_end = False
            self.unit_id = False