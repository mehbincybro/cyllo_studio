# -*- coding: utf-8 -*-
from odoo import fields, models


class ResignationRequestConfirm(models.Model):
    """The model is used to perform the functions
     when an employee confirm the resignation request"""
    _name = 'resignation.request.confirm'
    _description = 'Resignation Request Confirm'

    employee_id = fields.Many2one('hr.employee', help='To choose the employee',
                                  default=lambda self: self.env.user.employee_id.id)
    reference = fields.Char(help='To get the reference of the request', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', required=True)

    def action_confirm_resignation(self):
        """The function is used to confirm the employee resignation request,
         if yes an email send to the department manager"""
        if self.employee_id:
            self.employee_id.is_resigned = True
        request = self.env['employee.resignation'].sudo().search([('reference', '=', self.reference)])
        for rec in request:
            rec.write({
                'confirmed_date': fields.datetime.now(),
                'state': 'confirm'
            })
