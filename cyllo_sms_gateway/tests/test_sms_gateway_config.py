# -*- coding: utf-8 -*-
from odoo.addons.cyllo_sms_gateway.tests.common import TestCylloSmsGateway


class TestSmsGatewayConfig(TestCylloSmsGateway):

    def test_action_test_connection(self):
        action = self.sms_gateway.action_test_connection()
        self.assertEqual(action['name'], 'Send SMS')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'send.sms')
        self.assertEqual(action['context'], {'default_sms_id': self.sms_gateway.id})
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')

    def test_action_activate(self):
        self.sms_gateway.action_activate()
        self.assertTrue(self.sms_gateway.is_active)

    def test_action_deactivate(self):
        self.sms_gateway.action_deactivate()
        self.assertFalse(self.sms_gateway.is_active)
        self.assertFalse(self.sms_gateway.company_id)
        reset_fields = {
            "D7": ["d7_api"],
            "TWILIO": ["twilio_phone_number", "twilio_account_sid", "twilio_auth_token"],
            "CLICK SEND": ["click_send_api", "click_send_email"]
        }
        for gateway_type, fields in reset_fields.items():
            if self.sms_gateway.name == gateway_type:
                for field in fields:
                    self.assertEqual(getattr(self.sms_gateway, field), "")


