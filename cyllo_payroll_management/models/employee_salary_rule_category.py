# -*- coding: utf-8 -*-
from odoo import fields, models


class EmployeeSalaryRuleCategory(models.Model):
    """To create the salary rule category"""
    _name = 'employee.salary.rule.category'
    _description = 'Employee Salary Rule Category'

    name = fields.Char(help='To Add the name', required=True)
    code = fields.Char(help='To Add the code', required=True)
    parent_id = fields.Many2one(string='Parent Category', comodel_name='employee.salary.rule.category',
                                help='To choose the parent category')
    description = fields.Html(help='To add the description of the category')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
