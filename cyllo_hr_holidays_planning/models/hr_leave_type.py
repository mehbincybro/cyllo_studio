# -*- coding: utf-8 -*-
from odoo import fields, models


class HrLeaveType(models.Model):
    """Inherited model for hr.leave.type with additional fields."""
    _inherit = 'hr.leave.type'

    planning_allocation_type_id = fields.Many2one('allocation.type')
