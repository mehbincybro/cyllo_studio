# -*- coding: utf-8 -*-
from email.policy import default

from odoo import api,fields, models
import json

class QualityInspection(models.Model):
    _name = 'quality.inspection'
    _description = 'Quality Inspections'


    quality_control_id = fields.Many2one('quality.control.point', string='Quality Control Point')
    inspection_action_id = fields.Many2one('inspection.action', string='Actions', required=True)
    inspection_type_id = fields.Many2one('inspection.type', string='Type')
    value = fields.Json(default=lambda self: {
        "unit": {
            "id": False,
            "name": ''
        },
        "value": ''
    })
    is_measure = fields.Boolean(compute='_compute_is_measure')
    instruction = fields.Text(string='Quality Check Instructions')

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


