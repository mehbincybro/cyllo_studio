# -*- coding: utf-8 -*-
from odoo.addons.cyllo_accounting_pdc.tests.common import TestCylloAccountingPdc


class TesAccountJournal(TestCylloAccountingPdc):

    def test_default_outbound_payment_methods(self):
        self.assertTrue(
            self.account_journal._default_outbound_payment_methods().mapped(
                'name').index('PDC'))

    def test_default_inbound_payment_methods(self):
        self.assertTrue(
            self.account_journal._default_inbound_payment_methods().mapped(
                'name').index('PDC'))

    def test_compute_available_payment_method_ids(self):
        self.assertTrue(
            self.account_journal.available_payment_method_ids.mapped(
                'name').index('PDC'))
