# -*- coding: utf-8 -*-
from odoo.addons.cyllo_sms_gateway.tests.common import TestCylloSmsGateway


class TestSendSms(TestCylloSmsGateway):

    def test_onchange_partner_ids(self):
        self.send_sms._onchange_partner_ids()
        self.assertEqual('+9876543210', self.send_sms.sms_to)

    def test_action_send_sms(self):
        self.send_sms.sms_id.d7_api = "Lopsurt+777777"
        action = self.send_sms.action_send_sms()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')
        self.assertEqual(action['params']['message'],
                         "TwilioException('Credentials are required to create a TwilioClient')")

    def test_create_sms_history(self):
        self.send_sms.create_sms_history('Success')
        sms_history = self.env['sms.history'].search([
            ('user_id', '=', self.env.user.id),
            ('sms_gateway_id', '=', self.send_sms.sms_id.id),
            ('sms_mobile', '=', self.send_sms.sms_to),
            ('sms_text', '=', self.send_sms.text),
            ('sms_status', '=', 'Success'),
        ])
        self.assertTrue(sms_history, "SMS history record should be created")
