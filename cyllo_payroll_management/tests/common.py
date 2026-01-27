# -*- coding: utf-8 -*-
import datetime
import logging
from datetime import time

from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestPayrollManagementBase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.employee_01 = cls.env['hr.employee'].create({'name': 'John'})
        cls.department = cls.env['hr.department'].create({
            'name': 'Software Developer',
        })

        cls.structure_type = cls.structure_type = cls.env[
            'salary.structure.type'].create({
            'name': 'Employee',
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Attendance',
            'is_leave': False,
            'code': 'TESTWORK100',
        })

        cls.salary_structure_01 = cls.env['employee.salary.structure'].create({
            'name': 'Employee Salary Structure',
            'type_id': cls.structure_type.id,
            'code': 'BASE',
        })

        cls.unpaid_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Unpaid',
            'is_leave': True,
            'code': 'TESTUNPAID100',
            'round_days': 'half',
            'round_type': 'down',
            'unpaid_structure_ids': cls.salary_structure_01.ids
        })

        cls.salary_structure = cls.env['employee.salary.structure'].create({
            'name': 'Employee Salary Structure',
            'type_id': cls.structure_type.id,
            'code': 'BASE',
            'unpaid_work_entry_type_ids': [
                (4, cls.unpaid_work_entry_type.id, False)]
        })

        cls.work_entry_type_leave = cls.env['hr.work.entry.type'].create({
            'name': 'Leave',
            'is_leave': True,
            'code': 'TESTLEAVE200'
        })

        cls.hra_rule = cls.env['employee.salary.rule'].create({
            'name': 'House Rent Allowance',
            'sequence': 1,
            'amount_select': 'percentage',
            'amount_percentage': 35.0,
            'amount_percentage_base': 'contract.wage',
            'code': 'HRA',
            'category_id': cls.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id,
        })

        cls.mv_rule = cls.env['employee.salary.rule'].create({
            'name': 'Meal Voucher',
            'sequence': 2,
            'amount_select': 'fix',
            'amount_fix': 20,
            'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
            'code': 'MA',
            'category_id': cls.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id,
        })

        cls.sum_of_alw = cls.env['employee.salary.rule'].create({
            'name': 'Sum of Allowance category',
            'sequence': 3,
            'amount_select': 'code',
            'amount_python_compute': "result = payslip._sum_category('ALW', payslip.start_date, to_date=payslip.to_date)",
            'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
            'code': 'SUMALW',
            'category_id': cls.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id,
        })
        cls.calendar_40h = cls.env['resource.calendar'].create(
            {'name': 'Default calendar'})
        cls.hr_attendance_01 = cls.env['hr.attendance'].create({
            'employee_id': cls.employee_01.id,
            'check_in': datetime.datetime(2024, 4, 1, 9, 0, 0),
            'check_out': datetime.datetime(2024, 4, 1, 18, 0, 0)
        })

        cls.contract_01 = cls.env['hr.contract'].create({
            'date_start': '2018-01-01',
            'name': 'Contract for John',
            'state': 'open',
            'wage': 5000,
            'employee_id': cls.employee_01.id,
            'resource_calendar_id': cls.calendar_40h.id,
            'employee_salary_structure_id': cls.salary_structure.id
        })

        cls.employee_payslip = cls.env['employee.payslip'].create({
            'employee_id': cls.employee_01.id,
            'contract_id': cls.contract_01.id,
            'structure_id': cls.salary_structure.id,
            'state': 'done',
            'start_date': '2024-04-01',
            'to_date': '2024-04-30'
        })

        cls.employee_batch = cls.env['employee.payslip.batch'].create({
            'name': 'March - 2024',
            'start_date': '2024-04-01',
            'end_date': '2024-04-30',
            'state': 'draft',
            'is_batch_payslip': False
        })
        cls.resignation_type = cls.env['resigned.reasons'].create({
            'name': 'Sick'
        })
        cls.resignation = cls.env['employee.resignation'].create({
            'employee_id': cls.employee_01.id,
            'contract_id': cls.contract_01.id,
            'joining_date': cls.contract_01.date_start,
            'end_date': cls.contract_01.date_end,
            'department_id': cls.department.id,
            'resignation_type_id': cls.resignation_type.id,
            'reason': 'Sick',
            'state': 'draft',
        })

        cls.employee_other_input = cls.env[
            'employee.payslip.other.input'].create({
            'name': 'Salary Input',
            'code': 'SALARY_INPUT'
        })

        cls.employee_salary_attachment = cls.env[
            'employee.salary.attachment'].create({
            'employee_id': cls.employee_01.id,
            'description': 'Attachment',
            'employee_payslip_other_input_id': cls.employee_other_input.id,
            'start_date': '2020-01-01',
            'end_date': '2024-01-01',
            'month_amount': 57,
            'state': 'running',
            'total_amount': 7000,
        })

    def create_work_entry(self, start, stop, work_entry_type=None):
        work_entry_type = work_entry_type or self.work_entry_type
        return self.env['hr.work.entry'].create({
            'contract_id': self.employee_01.contract_ids[0].id,
            'name': "Work entry %s-%s" % (start, stop),
            'date_start': start,
            'date_stop': stop,
            'employee_id': self.employee_01.id,
            'work_entry_type_id': work_entry_type.id,
        })
