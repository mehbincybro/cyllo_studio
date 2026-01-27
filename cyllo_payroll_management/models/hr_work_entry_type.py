# -*- coding: utf-8 -*-
from odoo import fields, models


class HrWorkEntryType(models.Model):
    """To inherit the field to make sure that the entry is for attendance"""
    _inherit = 'hr.work.entry.type'

    is_attendance = fields.Boolean(string='Attendance Entry', help='To choose entry for attendance')
    round_days = fields.Selection([('no', 'No Rounding'), ('half', 'Half Day'), ('full', 'Day')],
                                  string="Rounding", required=True, default='no',
                                  help="When the work entry is displayed in the payslip, the value is rounded "
                                       "accordingly.")
    round_type = fields.Selection([('closest', 'Closest'), ('down', 'Down'), ('up', 'UP')],
                                  help='Way of rounding work entry type', default='down')
    unpaid_structure_ids = fields.Many2many('employee.salary.structure',
                                            string="Unpaid in Structures Types",
                                            help="The work entry on the payslip does not result in any monetary "
                                                 "compensation for the employee.")
