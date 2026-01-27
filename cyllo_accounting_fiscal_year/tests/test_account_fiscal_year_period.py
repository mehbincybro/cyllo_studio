# -*- coding: utf-8 -*-
from odoo.addons.cyllo_accounting_fiscal_year.tests.common import TestCylloAccountingFiscalYear
from odoo.exceptions import UserError


class TestAccountFiscalYearPeriod(TestCylloAccountingFiscalYear):

    def test_unlink(self):
        with self.assertRaises(UserError):
            self.year_period.unlink()

    def test_button_close(self):
        self.year_period.action_close()
        self.assertEqual(self.year_period.state, 'close')

    def test_button_reopen(self):
        year_period = self.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'state': 'close',
            'fiscal_year_id': self.fiscal_year.id
        })
        year_period.action_reopen()
        self.assertEqual(year_period.state, 'open')

    def test_action_close_periods(self):
        year_period2 = self.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'state': 'open',
            'fiscal_year_id': self.fiscal_year.id
        })
        year_period2.action_close_periods()
        self.assertEqual(year_period2.state, 'close')

    def test_action_re_open_periods(self):
        year_period3 = self.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
            'state': 'close',
            'fiscal_year_id': self.fiscal_year.id
        })
        year_period3.action_re_open_periods()
        self.assertEqual(year_period3.state, 'open')
