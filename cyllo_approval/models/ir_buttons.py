# -*- coding: utf-8 -*-

from odoo import api,fields,models

class IrButtons(models.Model):
    _name = 'ir.buttons'
    _description = 'Ir Model Buttons'

    name = fields.Char('Name',required=True)
    string = fields.Char('String')
    view_id = fields.Many2one('ir.ui.view',string='View')
    model_id = fields.Many2one('ir.model',string='Model')

    @api.depends('string','name')
    def _compute_display_name(self):
        for button in self:
            name = button.name
            if button.string and button.name:
                name = f"{button.string}({name})"
            button.display_name = name
