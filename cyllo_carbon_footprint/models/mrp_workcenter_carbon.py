# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpWorkcenterCarbon(models.Model):
    _name = 'mrp.workcenter.carbon'
    _description = 'Manufacturing Operation Carbon Line'

    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation', ondelete='cascade', required=True)
    source_id = fields.Many2one('carbon.source', string='Name', required=True)
    unit_id = fields.Many2one('carbon.unit', string='Unit', related='source_id.activity_unit', readonly=False, store=True)

    @api.onchange('source_id')
    def _onchange_source_id(self):
        if self.source_id:
            self.unit_id = self.source_id.activity_unit
        else:
            self.unit_id = False
