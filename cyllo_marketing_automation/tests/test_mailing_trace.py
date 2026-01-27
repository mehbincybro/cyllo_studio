# -*- coding: utf-8 -*-
from odoo.tests import common


class TestMailingTrace(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in mailing_trace.

           Creates a marketing activity line and a mailing trace record.
        """
        super().setUpClass()
        cls.activity_line = cls.env['marketing.activity.line'].create(
            {'mail_clicked': False, 'mail_opened': False,
             'mail_replied': False,
             'mail_bounced': False})
        cls.mailing_trace = cls.env['mailing.trace'].create(
            {'failure_type': 'mail_dup',
             'model': 'res.partner',
             'record_id': cls.env.ref('hr.work_contact_mit').id,
             'marketing_activity_line_id': cls.activity_line.id,
             })

    def test_get_display_value(self):
        """
            Test the get_display_value method.

            Checks if the method returns the correct display value for a
            failure type.
        """
        fail_message = self.mailing_trace.failure_type
        value = self.mailing_trace.get_display_value(fail_message)
        self.assertEqual(value, 'Duplicated Email')

    def test_set_clicked(self):
        """
            Test the set_clicked method.

            Checks if the mail_clicked field is set to True.
        """
        self.mailing_trace.set_clicked()
        self.assertEqual(self.activity_line.mail_clicked, True)
        self.assertNotEqual(self.activity_line.mail_opened, False)

    def test_set_opened(self):
        """
            Test the set_opened method.

            Checks if the mail_opened field is set to True.
        """
        self.mailing_trace.set_opened()
        self.assertEqual(self.activity_line.mail_opened, True)

    def test_set_replied(self):
        """
            Test the set_replied method.

            Checks if the mail_opened field is set to True and mail_replied is
            not False.
        """
        self.mailing_trace.set_replied()
        self.assertEqual(self.activity_line.mail_opened, True)
        self.assertNotEqual(self.activity_line.mail_replied, False)

    def test_set_bounced(self):
        """
            Test the set_bounced method.

            Checks if the mail_bounced field is set to True.
        """
        self.mailing_trace.set_bounced()
        self.assertEqual(self.activity_line.mail_bounced, True)
