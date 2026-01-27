# -*- coding: utf-8 -*-
import datetime

from odoo.addons.cyllo_accounting_fiscal_year.tests.common import TestCylloAccountingFiscalYear
from odoo.exceptions import UserError


class TestAccountFiscalYear(TestCylloAccountingFiscalYear):

    def test_check_intersections(self):
        with self.assertRaises(UserError):
            self.env['account.fiscal.year'].create({
                'name': 'Year1',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'company_id': self.env.company.id,
                'state': 'draft'
            })
            self.env['account.fiscal.year'].create({
                'name': 'Year1',
                'start_date': '2025-01-01',
                'end_date': '2024-12-31',
                'company_id': self.env.company.id,
                'state': 'draft'
            })

    def test_get_domain(self):
        res = self.fiscal_year._get_domain()
        self.assertEqual(res[2][2], self.fiscal_year.id)
        self.assertEqual(res[3][2], self.fiscal_year.company_id.id)
        self.assertEqual(res[7], ('start_date', '<=', datetime.date(2021, 1, 1)))
        self.assertEqual(res[8], ('end_date', '>=', datetime.date(2021, 1, 1)))
        self.assertEqual(res[10], ('start_date', '<=', datetime.date(2021, 12, 31)))
        self.assertEqual(res[11], ('end_date', '>=', datetime.date(2021, 12, 31)))
        self.assertEqual(res[13], ('start_date', '>=', datetime.date(2021, 1, 1)))
        self.assertEqual(res[14], ('start_date', '<=', datetime.date(2021, 12, 31)))

    def test_unlink(self):
        fiscal_year1 = self.env['account.fiscal.year'].create({
            'name': 'Year1',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'company_id': self.env.company.id,
            'state': 'open'
        })
        with self.assertRaises(
                UserError, msg='You cannot delete a fiscal year in open state '
                               'first close the fiscal year.'):
            fiscal_year1.unlink()
        with self.assertRaises(UserError, msg='You cannot delete a fiscal year'
                                              ' if there is open periods'):
            self.fiscal_year2.unlink()

    def test_button_create_periods(self):
        with self.assertRaises(UserError, msg='There are already periods for '
                                              'the fiscal yea'):
            self.fiscal_year2.action_create_periods()

    def test_button_reopen(self):
        self.fiscal_year3.action_reopen()
        self.assertEqual(self.fiscal_year3.state, 'open')
        self.assertEqual(self.fiscal_year3.period_ids.state, 'open')

    def test_button_draft(self):
        self.fiscal_year.action_draft()
        self.assertEqual(self.fiscal_year.state, 'draft')

    def test_button_open(self):
        self.fiscal_year.action_open()
        self.assertEqual(self.fiscal_year.state, 'open')

