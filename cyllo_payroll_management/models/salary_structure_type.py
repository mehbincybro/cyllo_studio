# -*- coding: utf-8 -*-
from odoo import fields, models


class SalaryStructureType(models.Model):
    """To create employee contract """
    _name = 'salary.structure.type'
    _description = 'Salary Structure Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Structure Type', help='Name of the structure type', required=True)
    country_id = fields.Many2one('res.country', help='To choose the country',
                                 default=lambda self: self.env.company.country_id)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    default_wage_type = fields.Selection([('hourly', 'Hourly Wage'), ('fixed', 'Monthly Fixed Wage')],
                                         help='To add the wage', default='fixed')
    default_schedule_pay = fields.Selection([('daily', 'Daily'), ('monthly', 'Monthly'), ('weekly', 'Weekly')],
                                            help='To add the schedule pay', default='monthly')
    default_working_hour_id = fields.Many2one('resource.calendar', string='Working Schedule',
                                              help='To add the working time of the employee',
                                              default=lambda self: self.env.company.resource_calendar_id)
    salary_structure_id = fields.Many2one('employee.salary.structure',
                                          help='To choose the salary structure type', domain='[("type_id", "=", ''id)]')
    default_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Default Work Entry', help='To add the work entry ',
        default=lambda self: self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False))

