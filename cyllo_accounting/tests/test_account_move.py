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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountFiscalYear(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fiscal_year = cls.env['account.fiscal.year'].create({
            'name': 'Year 2023',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'company_id': cls.env.company.id,
            'state': 'draft',
        })
        cls.fiscal_year.action_open()

    def test_check_intersections(self):
        with self.assertRaises(UserError):
            self.env['account.fiscal.year'].create({
                'name': 'Year 2022',
                'start_date': '2022-01-01',
                'end_date': '2023-12-31',
                'company_id': self.env.company.id,
            })