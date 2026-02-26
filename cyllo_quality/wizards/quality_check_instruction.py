# -*- coding: utf-8 -*-
from odoo import fields, models


class QualityCheckInstruction(models.TransientModel):
    _name = 'quality.check.instruction'
    _description = 'Quality Check Instruction'

    inspection_id = fields.Many2one('quality.inspection')
    instruction = fields.Html(string='Instructions')

    def action_add_instruction(self):
        self.inspection_id.write({
            'instruction': self.instruction,
        })

