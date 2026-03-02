# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AlertWarning(models.TransientModel):
    _name = 'alert.warning'
    _description = 'Alert Warning'

    quality_check_id = fields.Many2one('quality.check')
    quality_check_line_id = fields.Many2one('quality.check.line')
    failure_location_id = fields.Many2one('stock.location', string='Failure Location', related='quality_check_id.quality_control_id.failure_location_id', readonly=False)

    def action_create_alert(self):
        stage_id = self.env.ref('cyllo_quality.quality_alert_stage_quarantine').id
        q = self.env['quality.alert'].create({
            'quality_check_id': self.quality_check_id.id,
            'product_id': self.quality_check_id.product_id.id if self.quality_check_id.product_id else 0,
            'picking_id': self.quality_check_id.picking_id.id if self.quality_check_id.picking_id else 0,
            'quality_team_id': self.quality_check_id.quality_team_id.id if self.quality_check_id.quality_team_id else 0,
            'stage_id': stage_id
        })
        self.quality_check_line_id.is_alert = True
