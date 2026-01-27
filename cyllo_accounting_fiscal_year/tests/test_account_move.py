# -*- coding: utf-8 -*-
from odoo.addons.cyllo_accounting_fiscal_year.tests.common import TestCylloAccountingFiscalYear
from odoo.exceptions import RedirectWarning, UserError


class TestAccountFiscalYear(TestCylloAccountingFiscalYear):

    def test_compute_fiscal_year_period(self):
        self.account_move._compute_fiscal_year_period()
        self.assertTrue(self.account_move.fiscal_year_id)
        self.assertTrue(self.account_move.period_id)

    def test_check_fiscalyear_lock_date(self):
        with self.assertRaises(UserError, msg='First Open the Fiscal Year'):
            self.account_move._check_fiscalyear_lock_date()
        fiscal_year = self.env['account.fiscal.year'].create({
            'name': 'Year1',
            'start_date': '2020-01-01',
            'end_date': '2020-12-31',
            'company_id': self.env.company.id,
            'state': 'open'
        })
        account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2020-10-05',
            'fiscal_year_id': fiscal_year.id,
            'period_id': self.year_period2.id
        })
        with self.assertRaises(RedirectWarning):
            account_move._check_fiscalyear_lock_date()
        fiscal_year = self.env['account.fiscal.year'].create({
            'name': 'Year1',
            'start_date': '2019-01-01',
            'end_date': '2019-12-31',
            'company_id': self.env.company.id,
            'state': 'open'
        })
        year_period2 = self.env['account.fiscal.year.period'].create({
            'name': 'period1',
            'start_date': '2019-01-01',
            'end_date': '2019-12-31',
            'state': 'open',
            'fiscal_year_id': fiscal_year.id
        })
        account_move = self.env['account.move'].create({
            'partner_id': self.partner.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': '2019-10-05',
            'fiscal_year_id': fiscal_year.id,
            'period_id': year_period2.id
        })
        self.assertTrue(account_move._check_fiscalyear_lock_date())
