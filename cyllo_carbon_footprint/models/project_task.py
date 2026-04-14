# -*- coding: utf-8 -*-
from odoo import api, fields, models

class Task(models.Model):
    _inherit = "project.task"

    reduced_emissions = fields.Float(string="Reduced Emissions (kgCO²e)")
    recycled_water = fields.Float(string="Recycled Water (KL)", help="Amount of recycled/recovered water in this task.")
    scope_id = fields.Many2one('carbon.scope', string="Scope")

    is_water_project = fields.Boolean(compute='_compute_project_type')
    is_green_project = fields.Boolean(compute='_compute_project_type')

    @api.depends('project_id', 'project_id.name')
    def _compute_project_type(self):
        for task in self:
            name = task.project_id.name or ''
            task.is_water_project = 'Water' in name
            task.is_green_project = 'Green' in name

