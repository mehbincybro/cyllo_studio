# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TestEmployeePayslipBatchList(TestPayrollManagementBase):
    """Test for employee batch list"""

    def test_compute_employee_ids(self):
        _logger.info('Test for compute employee ids')
        self.batch_list = self.env['employee.payslip.batch.list'].create({
            'batch_payslip_id': self.employee_batch.id,
            'department_id': self.department.id,
            'structure_id': self.salary_structure.id
        })
        self.batch_list._compute_employee_ids()
        self.assertTrue(self.batch_list.employee_ids)
        _logger.info('Test success for compute employee ids')

    def test_get_employee_ids(self):
        _logger.info('Test for employee ids')
        self.batch_list_01 = self.env['employee.payslip.batch.list'].create({
            'batch_payslip_id': self.employee_batch.id,
        })
        self.employees = self.batch_list_01._get_employee_ids()
        self.assertTrue(self.employees)
        _logger.info('Test success for employee ids')

    def test_action_compute_sheet(self):
        _logger.info('Test for compute sheet')
        with self.assertRaises(UserError) as UE:
            self.batch_list_02 = self.env['employee.payslip.batch.list'].create(
                {
                    'batch_payslip_id': self.employee_batch.id,
                })
            self.batch_list_02.action_compute_sheet()
        self.assertEqual(UE.exception.args[0], 'No active batch found.')
        _logger.info('Test success for compute sheet')
