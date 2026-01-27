# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestHrContract(TestPayrollManagementBase):
    """Test for hr contract"""

    def test_compute_yearly_wage(self):
        _logger.info('Test for yearly wage')
        self.contract_01._compute_yearly_wage()
        self.assertEqual(self.contract_01.yearly_wage, 60000)
        _logger.info('Test success for yearly wage')

    def test_action_approve_contract_validation(self):
        _logger.info('Test for approve contract')
        self.employee_02 = self.env['hr.employee'].create({'name': 'Johnson'})
        with self.assertRaises(ValidationError) as VE:
            self.contract_02 = self.env['hr.contract'].create({
                'date_start': '2018-01-01',
                'name': 'Contract for Johnson',
                'state': 'draft',
                'wage': 5000,
                'employee_id': self.employee_02.id,
                'resource_calendar_id': self.calendar_40h.id,
                'employee_salary_structure_id': self.salary_structure.id
            })
            self.contract_02.action_approve_contract()
        self.assertEqual(VE.exception.args[0],
                         'Please add the Training Start Date and End Date')
        _logger.info('Test success for approve contract validation')

    def test_action_approve_contract_training(self):
        _logger.info('Test for approve contract training')
        self.employee_03 = self.env['hr.employee'].create({'name': 'Michel'})
        self.contract_03 = self.env['hr.contract'].create({
            'training_date_from': '2017-12-31',
            'training_date_to': '2018-01-01',
            'date_start': '2018-01-01',
            'name': 'Contract for Michel',
            'state': 'draft',
            'wage': 5000,
            'employee_id': self.employee_03.id,
            'resource_calendar_id': self.calendar_40h.id,
            'employee_salary_structure_id': self.salary_structure.id
        })
        self.contract_03.action_approve_contract()
        self.assertEqual(self.contract_03.state, 'open')
        _logger.info('Test success for approve contract training')

    def test_onchange_state(self):
        _logger.info('Test for onchange state')
        self.employee_04 = self.env['hr.employee'].create(
            {'name': 'Michel john'})
        with self.assertRaises(ValidationError) as VE:
            self.contract_04 = self.env['hr.contract'].create({
                'training_date_from': '2017-12-31',
                'training_date_to': '2018-01-01',
                'name': 'Contract for Michel john',
                'state': 'training',
                'wage': 5000,
                'employee_id': self.employee_04.id,
                'resource_calendar_id': self.calendar_40h.id,
                'employee_salary_structure_id': self.salary_structure.id
            })
            self.contract_04._onchange_state()
        self.assertEqual(VE.exception.args[0],
                             'You cannot change the status of non-approved Contracts')
        _logger.info('Test success for onchange state')
