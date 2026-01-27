from odoo.addons.cyllo_advance_payment.tests.common import \
    TestCylloAdvancePayment
from odoo.exceptions import UserError


class TestAdvancePayment(TestCylloAdvancePayment):

    def test_default_get_sale_order(self):
        wizard = self.env['advance.payment'].with_context(type='sale',
                                                          active_id=1).default_get(
            [])
        self.assertEqual(wizard['communication'], 'Sale Order 1')
        self.assertEqual(wizard['total_amount'], 100.0)
        self.assertEqual(wizard['pay_amount'], 100.0)
        self.assertEqual(wizard['partner_id'], 1)
        self.assertEqual(wizard['currency_id'], 1)
        self.assertEqual(wizard['company_id'], 1)
        self.assertTrue(wizard['date'])

    def test_default_get_purchase_order(self):
        wizard = self.env['advance.payment'].with_context(type='purchase',
                                                          active_id=2).default_get(
            [])
        self.assertEqual(wizard['communication'], 'Purchase Order 2')
        self.assertEqual(wizard['total_amount'], 200.0)
        self.assertEqual(wizard['pay_amount'], 200.0)
        self.assertEqual(wizard['partner_id'], 2)
        self.assertEqual(wizard['currency_id'], 2)
        self.assertEqual(wizard['company_id'], 2)
        self.assertTrue(wizard['date'])

    def test_compute_journal_id(self):
        wizard = self.env['advance.payment'].create({})
        wizard._compute_journal_id()
        self.assertTrue(wizard.journal_id)

    def test_compute_total_amount(self):
        wizard = self.env['advance.payment'].create({})
        wizard._compute_total_amount()
        self.assertEqual(wizard.total_amount, 0.0)

    def test_compute_payment_method_line_id(self):
        wizard = self.env['advance.payment'].create({})
        wizard._compute_payment_method_line_id()
        self.assertTrue(wizard.payment_method_line_id)

    def test_onchange_pay_amount(self):
        wizard = self.env['advance.payment'].create({'total_amount': 100.0})
        wizard._onchange_pay_amount()
        self.assertEqual(wizard.amount_difference, 0.0)

        with self.assertRaises(UserError):
            wizard.pay_amount = 150.0
            wizard._onchange_pay_amount()

    def test_action_validate_payment(self):
        wizard = self.env['advance.payment'].create({'pay_amount': 100.0})
        wizard.action_validate_payment()
        payment = self.env['account.payment'].search([], order='id desc',
                                                     limit=1)
        self.assertEqual(payment.amount, 100.0)
        self.assertEqual(payment.payment_type, 'inbound')
        print('set')