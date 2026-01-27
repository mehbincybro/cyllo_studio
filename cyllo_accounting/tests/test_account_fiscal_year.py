# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import datetime

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountFiscalYear(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        today = fields.Date.today()
        cls.year = today.year

        # ------------------------------------------------------------
        # SAFE CLEANUP (respect business rules)
        # ------------------------------------------------------------
        fiscal_years = cls.env['account.fiscal.year'].search([
            ('company_id', '=', cls.company.id)
        ])

        # Move open fiscal years to draft before deleting
        fiscal_years.filtered(lambda fy: fy.state == 'open').action_draft()
        fiscal_years.unlink()

        # ------------------------------------------------------------
        # Base fiscal year for tests
        # ------------------------------------------------------------
        cls.fy_current = cls.env['account.fiscal.year'].create({
            'name': f'FY {cls.year}',
            'start_date': f'{cls.year}-01-01',
            'end_date': f'{cls.year}-12-31',
            'company_id': cls.company.id,
        })
        cls.fy_current.action_open()

    # ------------------------------------------------------------
    # CONSTRAINT TESTS
    # ------------------------------------------------------------

    def test_invalid_date_range(self):
        with self.assertRaises(UserError):
            self.env['account.fiscal.year'].create({
                'name': 'Invalid FY',
                'start_date': '2026-12-31',
                'end_date': '2026-01-01',
                'company_id': self.company.id,
            })

    def test_overlap_constraint(self):
        with self.assertRaises(UserError):
            self.env['account.fiscal.year'].create({
                'name': 'Overlap FY',
                'start_date': f'{self.year}-06-01',
                'end_date': f'{self.year}-12-31',
                'company_id': self.company.id,
            })

    def test_non_overlapping_allowed(self):
        fy_prev = self.env['account.fiscal.year'].create({
            'name': f'FY {self.year - 1}',
            'start_date': f'{self.year - 1}-01-01',
            'end_date': f'{self.year - 1}-12-31',
            'company_id': self.company.id,
        })
        self.assertTrue(fy_prev)

    # ------------------------------------------------------------
    # STATE ACTION TESTS
    # ------------------------------------------------------------

    def test_action_draft(self):
        self.fy_current.action_draft()
        self.assertEqual(self.fy_current.state, 'draft')

    def test_action_open(self):
        self.fy_current.action_open()
        self.assertEqual(self.fy_current.state, 'open')

    def test_action_reopen(self):
        self.fy_current.action_reopen()
        self.assertEqual(self.fy_current.state, 'open')

    # ------------------------------------------------------------
    # UNLINK TESTS
    # ------------------------------------------------------------

    def test_unlink_open_fiscal_year(self):
        with self.assertRaises(UserError):
            self.fy_current.unlink()

    def test_unlink_draft_fiscal_year(self):
        fy = self.env['account.fiscal.year'].create({
            'name': 'Draft FY',
            'start_date': f'{self.year + 1}-01-01',
            'end_date': f'{self.year + 1}-12-31',
            'company_id': self.company.id,
            'state': 'draft',
        })
        fy.unlink()
        self.assertFalse(fy.exists())

    # ------------------------------------------------------------
    # DOMAIN LOGIC TEST
    # ------------------------------------------------------------

    def test_get_domain(self):
        domain = self.fy_current._get_domain()
        overlap = self.env['account.fiscal.year'].search(domain)
        self.assertFalse(overlap)