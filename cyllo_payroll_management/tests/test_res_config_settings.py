# -*- coding: utf-8 -*-
import logging
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestResConfigSettings(TestPayrollManagementBase):
    """Test for settings"""
    def test_onchange_batch_move_line_true(self):
        _logger.info('Test for onchange batch move line')
        self.config_settings_model = self.env['res.config.settings']
        config_settings = self.config_settings_model.create({})
        config_settings.batch_move_line = True
        config_settings._onchange_batch_move_line()
        self.assertTrue(self.env.user.company_id.batch_move_line)
        _logger.info('Test success for onchange batch move line')

    def test_onchange_batch_move_line_false(self):
        _logger.info('Test for onchange batch move line')
        self.config_settings_model = self.env['res.config.settings']
        config_settings = self.config_settings_model.create({})
        config_settings.batch_move_line = False
        config_settings._onchange_batch_move_line()
        self.assertFalse(self.env.user.company_id.batch_move_line)
        _logger.info('Test success for onchange batch move line false')

