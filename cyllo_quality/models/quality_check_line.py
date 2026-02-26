# -*- coding: utf-8 -*-
from odoo import fields, models


class QualityCheckLine(models.Model):
    _name = 'quality.check.line'
    _description = 'Quality Check Lines'

    quality_check_id = fields.Many2one('quality.check')
    quality_control_id = fields.Many2one('quality.control.point', string='Quality Control Point')
    inspection_action_id = fields.Many2one('inspection.action', string='Actions', required=True)
    inspection_type_id = fields.Many2one('inspection.type', string='Type', required=True)
    quality_inspection_id = fields.Many2one('quality.inspection', string='Type')
    value = fields.Char()
    unit_value = fields.Json()
    note = fields.Text(string='Note')
    instruction = fields.Text(string='Quality Check Instructions')
    is_checked = fields.Boolean(copy=False)
    is_pass = fields.Boolean(copy=False)
    is_alert = fields.Boolean(copy=False)
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])

    def action_check_qc(self):
        quality_check = self.quality_check_id.read(['quality_check_line_ids', 'quality_control_id', 'product_id', 'user_id', 'quality_team_id'])
        return {
            'type': 'ir.actions.client',
            'tag': 'validate_quality_action',
            'name': 'Quality Check',
            'target': 'new',
            'context': {
                'quality_check': quality_check,
                'quality_check_action': self.read(),
            }
        }

    def validate_quality_actions(self, value, note):
        self.ensure_one()
        print("validate_quality_actions", self, value, self.inspection_action_id.name, note)
        if self.inspection_type_id.name in ['Measure', 'Instructions']:
            if self.value == value:
                self.write({
                    'status': 'pass'
                })
            else:
                self.write({
                    'status' : 'fail'})
        elif self.inspection_type_id.name in ['Pass/Fail', 'Take a picture']:
            if value == 'pass':
                self.write({
                    'status': 'pass'})
            else:
                self.write({
                    'status' : 'fail'})
        self.write({
            'is_checked': True,
            'note': note
        })
        return self.status

    def action_create_alert(self):
        return {
            'name': "Create Alert",
            'view_mode': 'form',
            'res_model': 'alert.warning',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_quality_check_id': self.quality_check_id.id,
                'default_quality_check_line_id': self.id,
            }
        }


