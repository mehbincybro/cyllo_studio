# -*- coding: utf-8 -*-
from odoo import fields, models


class PlanAllocation(models.Model):
    """This model extends the 'plan.allocation' model to add additional fields."""
    _inherit = 'plan.allocation'

    project_id = fields.Many2one('project.project', related='task_id.project_id')
    task_id = fields.Many2one('project.task', readonly=True)
