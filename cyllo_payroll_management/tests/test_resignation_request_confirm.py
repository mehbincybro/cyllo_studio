# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestResignationRequestConfirm(TestPayrollManagementBase):
    """Test for resignation request confirm"""

    def test_action_confirm(self):
        _logger.info('Test for action confirm')
        self.confirm = self.env['resignation.request.confirm'].create({
            'employee_id': self.employee_01.id,
            'department_id': self.employee_01.department_id.id
        })
        self.confirm.action_confirm_resignation()
        self.assertTrue(self.employee_01.is_resigned)
        _logger.info('Test success for action confirm')
