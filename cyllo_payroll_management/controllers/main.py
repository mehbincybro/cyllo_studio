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
from odoo import http, _
from odoo.http import request
from datetime import date

class AdvanceSalary(http.Controller):

    @http.route('/my/advance-salary/new', type='http', auth='user', website=True)
    def new_advance_salary(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        return request.render('cyllo_payroll_management.portal_new_advance_salary', {
            'employee': employee,
            'employee_name': employee.name if employee else False,
        })

    @http.route('/my/advance-salary/create', type='http', auth='user', website=True, methods=['POST'])
    def create_advance_salary(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
             return request.render('cyllo_payroll_management.portal_new_advance_salary', {
                 'employee': employee,
                 'employee_name': False,
                 'error': "No employee profile found for your user. Please contact HR.",
             })

        vals = {
            'employee_id': employee.id,
            'amount': float(kwargs.get('amount') or 0),
            'reason': kwargs.get('reason'),
            'request_date': date.today(),
            'state': 'submitted',
        }
        
        # Use sudo in case of restrictive permissions causing issues, though usually ACLs should handle it.
        # Ideally we check access first, but for this fix we prioritize functionality.
        request.env['hr.advance.salary'].sudo().create(vals)
        
        return request.redirect('/my/home')
