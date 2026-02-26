# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ValidateQualityCheck(models.TransientModel):
    _name = 'validate.quality.check'
    _description = 'Validate Quality Check'

    # quality_check_line_id = fields.Many2one('quality.check.line')
    # inspection_action_id = fields.Many2one('inspection.action')
    # value = fields.Char()
    # instruction = fields.Text(string='Quality Check Instructions')
    quality_control_point_id = fields.Many2many('quality.control.point')
    quality_check_wizard_line_ids = fields.Many2many('quality.check.line', compute='_compute_quality_check')

    @api.depends('quality_control_point_id')
    def _compute_quality_check(self):
        for action in self:
            print(action.quality_control_point_id.id)
            print(action.quality_control_point_id.quality_inspection_ids)
            action.quality_check_wizard_line_ids = [fields.Command.clear()]
            action.quality_check_wizard_line_ids = [fields.Command.create({
                'quality_control_id': action.quality_control_point_id.id,
                'inspection_action_id': qc.inspection_action_id.id,
                'quality_inspection_id': qc.inspection_type_id.id,
                'value': qc.value,
            }) for qc in action.quality_control_point_id.quality_inspection_ids]


    def action_validate_qc(self):
        print("dfcvgb")
    #     self.quality_check_line_id.is_checked = True
    #     if self.quality_check_line_id.value == self.value:
    #         self.quality_check_line_id.is_pass = True
    #         self.quality_check_line_id.status = 'pass'
    #     else:
    #         self.quality_check_line_id.is_pass = False
    #         self.quality_check_line_id.status = 'fail'
