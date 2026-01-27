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
from odoo.tests.common import TransactionCase


class TestCylloAccountingFiscalYear(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        company = cls.env.company

        cls.fiscal_year1 = cls.env['account.fiscal.year'].create({
            'name': 'FY 2015',
            'start_date': '2015-01-01',
            'end_date': '2015-12-31',
            'company_id': company.id,
            'state': 'open',
        })

        cls.fiscal_year2 = cls.env['account.fiscal.year'].create({
            'name': 'FY 2016',
            'start_date': '2016-01-01',
            'end_date': '2016-12-31',
            'company_id': company.id,
            'state': 'draft',
        })
