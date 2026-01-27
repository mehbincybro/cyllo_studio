# -*- coding: utf-8 -*-
from odoo.tests import common


class TestMarketingActivityLine(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_activity_line.

           Creates a marketing campaign, activity, participant, and
           activity line.
        """
        super().setUpClass()
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'Campaign 1'
        })
        cls.activity = cls.env['marketing.activity'].create({
            'name': 'Activity 1',
            'type': 'mail',
            'campaign_id': cls.campaign.id,
        })
        cls.participant = cls.env['marketing.participant'].create({
            'campaign_id': cls.campaign.id
        })
        cls.activity_line = cls.env['marketing.activity.line'].create({
            'activity_id': cls.activity.id,
            'participant_id': cls.participant.id,
            'mail_opened': False,
            'mail_clicked': False,
            'activity_another_trigger': False,
        })

    def test_trigger_next_activity(self):
        """
            Test the trigger_next_activity method.

            Checks if the trigger_next_activity method updates fields
            appropriately.
        """
        self.activity.sub_parent_activity_id = self.activity.id
        self.activity_line.trigger_next_activity('opened')
        self.assertEqual(self.activity_line.mail_opened, True)
        self.assertEqual(self.activity_line.mail_clicked, False)
        self.assertEqual(self.activity_line.activity_another_trigger, True)
