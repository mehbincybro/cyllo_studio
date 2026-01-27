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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EmployeeTrainingPeriod(models.Model):
    """To add the employees training period before the contract"""
    _name = 'employee.training.period'
    _description = 'Employee Training Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', help='To add the employee name', required=True)
    start_date = fields.Date(help='Start date of training', required=True)
    end_date = fields.Date(help='End date of training', required=True)
    job_position_id = fields.Many2one(related="employee_id.job_id", help="Current employee job position")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    time_off_ids = fields.Many2many('hr.leave', help='Time off allocated')
    state = fields.Selection([('new', 'New'), ('done','Completed'), ('extended', 'Extended')], required=True, default='new')

    @api.onchange('start_date', 'end_date')
    def _onchange_start_date(self):
        """Check if start_date is before or equal to end_date."""
        if self.start_date and self.end_date and not self.start_date < self.end_date:
            raise ValidationError(_("End date must be grater than the start date"))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Check whether the employee already has a training period."""
        if self.employee_id:
            existing_training_periods = self.env['employee.training.period'].search(
                [('employee_id', '=', self.employee_id.id)])
            if existing_training_periods:
                raise ValidationError(_("This employee already has a training period."))
