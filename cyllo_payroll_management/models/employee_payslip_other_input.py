# -*- coding: utf-8 -*-
from odoo import fields, models


class EmployeePayslipOtherInput(models.Model):
    """ Manage additional inputs for employee payslips under Payslip Other Input."""
    _name = 'employee.payslip.other.input'
    _description = 'Payslip Other Input'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, help='Description of the other input')
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    structure_ids = fields.Many2many('employee.salary.structure', string='Availability in Structure',
                                     help='This input will be only available in those structure.If empty, it will be'
                                          'available in all payslip.')
    company_id = fields.Many2one('res.company', copy=False, default=lambda self: self.env.company.id,
                                 help='The company associated with this record')
