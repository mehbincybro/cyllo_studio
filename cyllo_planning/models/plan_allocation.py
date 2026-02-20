# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models,_


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
    is_conflict = fields.Boolean(compute='_compute_conflict_data', store=True)

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

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        """Compute duration from start date and end date."""
        for allocation in self:
            allocation.duration = self._get_duration(allocation.start_datetime, allocation.end_datetime)

    def _get_duration(self, start_datetime, end_datetime):
        """Calculate duration between two datetimes using company hours/day logic."""
        if not start_datetime or not end_datetime or end_datetime < start_datetime:
            return 0

        calendar = self.env.company.resource_calendar_id

        hours_per_day = calendar.hours_per_day if calendar else 12

        # Case 1: Same day → actual hours, but max hours_per_day
        if start_datetime.date() == end_datetime.date():
            duration = (end_datetime - start_datetime).total_seconds() / 3600
            return round(min(duration, hours_per_day), 2)

        # Case 2: Multi-day → use calendar hours_per_day × days
        days = (end_datetime.date() - start_datetime.date()).days + 1
        return round(days * hours_per_day, 2)

    @api.depends('start_datetime', 'end_datetime', 'employee_id')
    def _compute_conflict_data(self):
        """Compute if the allocation conflicts with other allocations."""
        for allocation in self:
            allocation.is_conflict = allocation._check_overlap()

    def _check_overlap(self):
        """Check if the current allocation overlaps with existing allocations for the same employee."""
        self.ensure_one()
        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return False

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
            ('id', '!=', self.id),
        ]
        return bool(self.search_count(domain))

    @api.onchange('start_datetime', 'end_datetime', 'employee_id')
    def _onchange_check_overlap(self):
        """Warn user if the new allocation overlaps with existing ones."""
        if not self.start_datetime or not self.end_datetime or not self.employee_id:
            return

        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('start_datetime', '<', self.end_datetime),
            ('end_datetime', '>', self.start_datetime),
            ('id', '!=', self.id or self._origin.id),
        ]

        if self.search_count(domain):
            return {
                'warning': {
                    'title': _("Conflict Detected"),
                    'message': _("This employee has another plan scheduled during this time period."),
                }
            }
