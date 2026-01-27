# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    """To add understand the employee which is resigned"""
    _inherit = 'hr.employee'

    is_resigned = fields.Boolean(string='Resigned', help='To check if the employee has resigned or not')
    payslip_count = fields.Integer(compute='_compute_payslip_count', help='Total number of payslip for the employee')

    def _compute_payslip_count(self):
        """Compute the number of payslips generated for each employee"""
        for record in self:
            record.payslip_count = self.env['employee.payslip'].sudo().search_count([('employee_id', '=', record.id)])

    @api.model
    def update_employee_state(self):
        """Method to update employee state based on resignation data."""
        today = fields.Date.today()
        resignations_to_update = self.env['employee.resignation'].sudo().search(
            [('leaving_date', '<=', today), ('state', '=', 'approved')])
        for resignation in resignations_to_update:
            resignation.employee_id.write({'active': False})

    def action_view_payslip(self):
        """To view corresponding payslip of the employee"""
        return {
            'name': 'Payslip',
            'view_mode': 'tree,form',
            'res_model': 'employee.payslip',
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.id)],
        }
