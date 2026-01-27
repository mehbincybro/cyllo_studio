# -*- coding: utf-8 -*-
from odoo.addons.cyllo_advance_payment.tests.common import \
    TestCylloAdvancePayment


class TestSale(TestCylloAdvancePayment):
    def test_compute_total_advance_amount(self):
        self.assertEqual(self.sale_order.total_advance_amount,
                         (self.payment.amount + self.payment2.amount))

    def test_action_advance_payment(self):
        payment = self.sale_order.action_advance_payment()
        self.assertEqual(payment['name'], 'Advance Payment')
        self.assertEqual(payment['view_type'], 'form')
        self.assertEqual(payment['view_mode'], 'form')
        self.assertEqual(payment['target'], 'new')
