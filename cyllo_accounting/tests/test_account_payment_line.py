# -*- coding: utf-8 -*-
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting


class TestAccountPaymentLine(TestCylloAccounting):

    def test_compute_paid_amount(self):
        payment_line = self.env['account.payment.line'].create({
            'payment_id': self.payment.id,
            'move_id': self.account_move.id,
            'partner_id': self.partner.id,
        })
        payment_line._compute_paid_amount()
        self.assertEqual(payment_line.paid_amount, 0.0)
