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
from odoo import models, fields, api,_


class SalaryCalculator(models.TransientModel):
    _name = 'salary.calculator'
    _description = 'Gross-Net Salary Calculator'

    # Inputs
    is_employee_based = fields.Boolean(string="Based on Employee",
                                       default=False)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    struct_id = fields.Many2one('employee.salary.structure',
                                string="Salary Structure", required=True)
    work_schedule_id = fields.Many2one('resource.calendar',
                                       string="Working Schedule")

    salary = fields.Monetary(string="Salary", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda
        self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)

    # Computed Result Fields
    gross_month = fields.Monetary(compute="_compute_results")
    net_month = fields.Monetary(compute="_compute_results")
    cost_month = fields.Monetary(compute="_compute_results")
    cost_year = fields.Monetary(compute="_compute_results")

    @api.onchange('employee_id', 'is_employee_based')
    def _onchange_employee_id(self):
        if self.is_employee_based and self.employee_id:
            contract = self.employee_id.contract_id
            if contract:
                self.salary = contract.wage
                self.struct_id = contract.employee_salary_structure_id
                self.work_schedule_id = contract.resource_calendar_id
            else:
                return {
                    'warning': {
                        'title': _("No Active Contract Found"),
                        'message': _(
                            "The selected employee %s does not have an active or valid contract. Please configure a contract first ") % self.employee_id.name
                    }
                }
        elif not self.is_employee_based:
            self.employee_id = False

    @api.depends('salary', 'struct_id', 'employee_id', 'is_employee_based')
    def _compute_results(self):
        for rec in self:
            rec.gross_month = 0.0
            rec.net_month = 0.0
            rec.cost_month = 0.0
            rec.cost_year = 0.0

            if not rec.struct_id:
                continue

            # Create a 'virtual' payslip record
            payslip_vals = {
                'employee_id': rec.employee_id.id if rec.is_employee_based else False,
                'structure_id': rec.struct_id.id,
                'company_id': rec.company_id.id,
                'start_date': fields.Date.today().replace(day=1),
                'to_date': fields.Date.today(),
            }

            contract = False
            if rec.is_employee_based and rec.employee_id.contract_id:
                contract = rec.employee_id.contract_id
                payslip_vals['contract_id'] = contract.id

            # Create the virtual payslip
            payslip = self.env['employee.payslip'].new(payslip_vals)
            
            # If employee based, we can use the actual contract's worked days and rules
            if contract:
                payslip._onchange_employee_id()
                line_values = payslip._get_payslip_lines([contract.id], payslip)

                gross = 0.0
                net = 0.0
                employer_costs = 0.0

                for line in line_values:
                    print('line', line)
                    code = line.get('code')
                    print('code', code)
                    category_id = line.get('category_id')
                    print('category_id', category_id)
                    category = self.env['employee.salary.rule.category'].browse(category_id)
                    print('category', category.name)
                    total = line.get('amount', 0.0) * line.get('quantity', 1.0) * line.get('rate', 100.0) / 100.0
                    print('total', total)
                    if code == 'GROSS':
                        gross = total
                    elif code == 'NET':
                        net = total
                    elif category.code == 'COMP':
                        employer_costs += total

                rec.gross_month = gross
                rec.net_month = net
                rec.cost_month = gross + employer_costs
                rec.cost_year = rec.cost_month * 12
            elif not rec.is_employee_based and rec.salary:
                # Simple fallback for manual entry if no contract simulation is possible
                # In this case we just use the entered salary as basic/gross/net estimate
                rec.gross_month = rec.salary
                rec.net_month = rec.salary
                rec.cost_month = rec.salary
                rec.cost_year = rec.salary * 12
