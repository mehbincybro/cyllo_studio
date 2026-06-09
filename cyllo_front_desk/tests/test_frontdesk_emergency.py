# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestFrontdeskEmergency(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1. Create a Station
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'HQ Reception'
        })
        
        # 2. Get the Security Group
        cls.security_group = cls.env.ref('cyllo_front_desk.group_frontdesk_security')
        
        # 3. Create an Emergency Alert configuration
        cls.alert = cls.env['frontdesk.emergency.alert'].create({
            'name': 'Intruder Alert',
            'station_ids': [(4, cls.station.id)],
            'recipient_security': True,
            'default_message': 'Intruder detected. Seek shelter.',
        })

    def test_emergency_alert_flow(self):
        # 1. Create the Wizard
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': self.alert.default_message,
        })
        
        # 2. Verify onchange populates message
        wizard._onchange_alert_id()
        self.assertEqual(wizard.message, 'Intruder detected. Seek shelter.')

        # 3. Trigger action_send_alert
        action = wizard.action_send_alert()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        
        # 4. Verify log creation
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertTrue(log.exists())
        self.assertEqual(log.station_id, self.station)
        self.assertEqual(log.alert_id, self.alert)
        self.assertEqual(log.message, 'Intruder detected. Seek shelter.')
        self.assertIn('Security Team', log.recipient_summary)
