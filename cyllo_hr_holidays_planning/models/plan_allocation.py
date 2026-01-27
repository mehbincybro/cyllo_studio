# -*- coding: utf-8 -*-
from odoo import fields, models


class PlanAllocation(models.Model):
    """Inherited model for plan.allocation with additional fields."""
    _inherit = 'plan.allocation'

    leave_id = fields.Many2one('hr.leave', "Time off")
