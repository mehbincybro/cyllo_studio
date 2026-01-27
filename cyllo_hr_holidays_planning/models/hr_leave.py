# -*- coding: utf-8 -*-
from odoo import models


class HrLeave(models.Model):
    """Inherited model for hr.leave with additional methods"""
    _inherit = 'hr.leave'

    def action_approve(self):
        """Extends the approval function to generate planning if the planning
         allocation is set to time-off type."""
        res = super().action_approve()
        for record in self:
            allocation_type = record.holiday_status_id.planning_allocation_type_id
            if allocation_type and record.holiday_type == 'employee':
                self.env['plan.allocation'].create(
                    [{'allocation_type_id': allocation_type.id,
                      'employee_id': employee.id,
                      'start_datetime': record.date_from,
                      'end_datetime': record.date_to,
                      'leave_id': record.id} for employee in record.employee_ids])
        return res

    def action_refuse(self):
        """Extends the refuse function to delete corresponding planning."""
        res = super().action_refuse()
        self.env['plan.allocation'].search([('leave_id', 'in', self.ids)]).unlink()
        return res
