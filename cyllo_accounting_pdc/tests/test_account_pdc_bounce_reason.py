# -*- coding: utf-8 -*-
from odoo.addons.cyllo_accounting_pdc.tests.common import TestCylloAccountingPdc


class TestAccountPdcBounceReason(TestCylloAccountingPdc):

    def test_action_bounce(self):
        bounce_reason = self.env['account.pdc.bounce.reason'].create({
            'reason': 'No Balance',
            'bank_name': 'ABC',
            'cheque_reference': 'Test Ref',
            'pdc_payment_id': self.pdc_payment.id
        })
        bounce_reason.action_bounce()
        self.assertEqual(bounce_reason.pdc_payment_id.payment_status,
                         'bounced')
