# -*- coding: utf-8 -*-
import logging
import datetime

from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

from odoo import fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestGratuitySettlement(TestPayrollManagementBase):
    """Test for gratuity settlement"""

    def test_onchange_employee_id(self):
        _logger.info('Test for onchange employee id')
        today = fields.Date.today()
        self.journal = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_01 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_01 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_01 = self.env[
            'gratuity.configuration'].create(
            {
                'name': 'Gratuity Configuration',
                'contract_type': 'limited',
                'start_date': today - datetime.timedelta(
                    days=1),
                'end_date': today + datetime.timedelta(
                    days=1),
                'journal_id': self.journal.id,
                'credit_account_id': self.credit_account_01.id,
                'debit_account_id': self.debit_account_01.id
            })
        with self.assertRaises(ValidationError) as VE:
            self.settlement = self.env['gratuity.settlement'].create({
                'employee_id': self.employee_01.id,
                'state': 'draft',
                'basic_salary': 5000,
                'contract_type': 'limited',
                'gratuity_configuration_id': self.gratuity_configuration_01.id,
                'credit_account_id': self.credit_account_01.id,
                'debit_account_id': self.debit_account_01.id,
                'journal_id': self.journal.id
            })
            self.settlement._onchange_employee_id()
        self.assertEqual(VE.exception.args[0],
                         'No gratuity configuration found, please check the dates.')
        _logger.info('Test success for onchange employee id')

    def test_onchange_employee_id_configuration(self):
        _logger.info('Test for onchange employee configuration')
        today = fields.Date.today()
        self.journal_01 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_02 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_02 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_02 = self.env[
            'gratuity.configuration'].create(
            {
                'name': 'Gratuity Configuration',
                'contract_type': 'unlimited',
                'start_date': today - datetime.timedelta(
                    days=1),
                'end_date': today + datetime.timedelta(
                    days=1),
                'journal_id': self.journal_01.id,
                'credit_account_id': self.credit_account_02.id,
                'debit_account_id': self.debit_account_02.id
            })
        with self.assertRaises(ValidationError) as VE:
            self.settlement_01 = self.env['gratuity.settlement'].create({
                'employee_id': self.employee_01.id,
                'state': 'draft',
                'basic_salary': 5000,
                'contract_type': 'unlimited',
                'gratuity_configuration_id': self.gratuity_configuration_02.id,
                'credit_account_id': self.credit_account_02.id,
                'debit_account_id': self.debit_account_02.id,
                'journal_id': self.journal_01.id
            })
            self.settlement_01._onchange_employee_id()
        self.assertEqual(VE.exception.args[0],
                         'No configuration for an acceptable gratuity was found!')
        _logger.info('Test success for onchange employee configuration')

    def test_action_submit(self):
        _logger.info('Test for action submit')
        today = fields.Date.today()
        self.journal_02 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_03 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_03 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_03 = self.env[
            'gratuity.configuration'].create(
            {
                'name': 'Gratuity Configuration',
                'contract_type': 'unlimited',
                'start_date': today - datetime.timedelta(
                    days=1),
                'end_date': today + datetime.timedelta(
                    days=1),
                'journal_id': self.journal_02.id,
                'credit_account_id': self.credit_account_03.id,
                'debit_account_id': self.debit_account_03.id
            })
        self.settlement_02 = self.env['gratuity.settlement'].create({
            'employee_id': self.employee_01.id,
            'state': 'draft',
            'basic_salary': 5000,
            'contract_type': 'unlimited',
            'gratuity_configuration_id': self.gratuity_configuration_03.id,
            'credit_account_id': self.credit_account_03.id,
            'debit_account_id': self.debit_account_03.id,
            'journal_id': self.journal_02.id
        })
        self.settlement_02.action_submit()
        self.assertEqual(self.settlement_02.state, 'submit')
        _logger.info('Test success for action submit')

    def test_action_approve(self):
        _logger.info('Test for action approve')
        today = fields.Date.today()
        self.journal_03 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_04 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_04 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_04 = self.env[
            'gratuity.configuration'].create(
            {
                'name': 'Gratuity Configuration',
                'contract_type': 'unlimited',
                'start_date': today - datetime.timedelta(
                    days=1),
                'end_date': today + datetime.timedelta(
                    days=1),
                'journal_id': self.journal_03.id,
                'credit_account_id': self.credit_account_04.id,
                'debit_account_id': self.debit_account_04.id
            })
        self.settlement_03 = self.env['gratuity.settlement'].create({
            'employee_id': self.employee_01.id,
            'state': 'draft',
            'basic_salary': 5000,
            'contract_type': 'unlimited',
            'gratuity_configuration_id': self.gratuity_configuration_04.id,
            'credit_account_id': self.credit_account_04.id,
            'debit_account_id': self.debit_account_04.id,
            'journal_id': self.journal_03.id
        })
        self.settlement_02.action_approve()
        self.assertEqual(self.settlement_03.state, 'approve')
        _logger.info('Test success for action approve')

    def test_action_cancel(self):
        _logger.info('Test for action cancel')
        today = fields.Date.today()
        self.journal_04 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_04 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_04 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_04 = self.env[
            'gratuity.configuration'].create(
            {
                'name': 'Gratuity Configuration',
                'contract_type': 'unlimited',
                'start_date': today - datetime.timedelta(
                    days=1),
                'end_date': today + datetime.timedelta(
                    days=1),
                'journal_id': self.journal_04.id,
                'credit_account_id': self.credit_account_04.id,
                'debit_account_id': self.debit_account_04.id
            })
        self.settlement_04 = self.env['gratuity.settlement'].create({
            'employee_id': self.employee_01.id,
            'state': 'draft',
            'basic_salary': 5000,
            'contract_type': 'unlimited',
            'gratuity_configuration_id': self.gratuity_configuration_04.id,
            'credit_account_id': self.credit_account_04.id,
            'debit_account_id': self.debit_account_04.id,
            'journal_id': self.journal_03.id
        })
        self.settlement_02.action_cancel()
        self.assertEqual(self.settlement_04.state, 'cancel')
        _logger.info('Test success for action cancel')
