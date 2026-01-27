# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TestEmployeeTrainingPeriod(TestPayrollManagementBase):
    """Test for employee training period"""

    def test_onchange_start_date(self):
        _logger.info('Test for onchange start date')
        with self.assertRaises(ValidationError) as VE:
            self.employee_training_period = self.env[
                'employee.training.period'].create({
                'employee_id': self.employee_01.id,
                'start_date': '2018-02-02',
                'end_date': '2018-01-01',
                'state': 'new'
            })
            self.employee_training_period._onchange_start_date()
        self.assertEqual(VE.exception.args[0],'End date must be grater than the start date')
        _logger.info('Test success for onchange start date')

    def test_onchange_employee_id(self):
        _logger.info('Test for onchange existing training period')
        with self.assertRaises(ValidationError) as VE:
            self.employee_training_period = self.env[
                'employee.training.period'].create({
                'employee_id': self.employee_01.id,
                'start_date': '2018-01-01',
                'end_date': '2018-02-02',
                'state': 'new'
            })
            existing_period = self.employee_training_period
            existing_period._onchange_employee_id()
        self.assertEqual(VE.exception.args[0],'This employee already has a training period.')
        _logger.info('Test success for onchange existing training period')


