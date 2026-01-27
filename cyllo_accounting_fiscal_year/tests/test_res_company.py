# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.cyllo_accounting_fiscal_year.tests.common import TestCylloAccountingFiscalYear


class TestResCompany(TestCylloAccountingFiscalYear):

    def test_compute_fiscalyear_dates(self):
        company = self.env.company
        self.assertTrue(company.compute_fiscalyear_dates(fields.Date.today()))
