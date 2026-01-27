# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PlanAllocation(models.Model):
    """Represents planning allocation."""
    _name = 'plan.allocation'
    _description = "Planning Allocation"

    name = fields.Char(compute='_compute_name')
    start_datetime = fields.Datetime(string="From", required=True)
    end_datetime = fields.Datetime(string="To", required=True)
    duration = fields.Float(compute='_compute_duration', store=True, readonly=False)
    description = fields.Text(help="Planning allocation description")
    employee_id = fields.Many2one('hr.employee', required=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, string="Created By")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    allocation_type_id = fields.Many2one('allocation.type', required=True)
    color = fields.Char(related='allocation_type_id.color')

    _sql_constraints = [
        ('check_period_validation', 'CHECK(end_datetime >= start_datetime)',
            'End date should be greater than start date'),
    ]

    @api.depends('allocation_type_id', 'employee_id')
    def _compute_name(self):
        """The name of the allocation is computed by using start date and end date."""
        for allocation in self:
            allocation.name = ((f"{allocation.employee_id.name} " if allocation.employee_id else '') +
                               (f"{allocation.allocation_type_id.name}" if allocation.allocation_type_id else '')
                               or 'New')

    def _get_duration(self, start_datetime, end_datetime):
        """ Retrieve the duration value between the two given dates."""
        if not start_datetime or not end_datetime:
            return 0
        duration = (end_datetime - start_datetime).total_seconds() / 3600
        return round(duration, 2)

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        """Compute duration from start date and end date."""
        for allocation in self:
            allocation.duration = self._get_duration(allocation.start_datetime, allocation.end_datetime)
