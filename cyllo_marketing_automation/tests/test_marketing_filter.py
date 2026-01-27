# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common


class TestMarketingFilter(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_filter.

           Creates a valid marketing filter.
        """
        super().setUpClass()
        cls.valid_filter = cls.env['marketing.filter'].create({
            'name': 'Valid Filter',
            'user_id': cls.env.user.id,
            'model_id': cls.env.ref('hr.model_hr_department').id,
            'domain': [('id', '=', 1)],
        })

    def test_check_domain(self):
        """
            Test the _check_domain method.

            Checks if the method correctly validates the domain for the filter.
        """
        self.valid_filter._check_domain()
        vals = {
            'name': 'Invalid Filter',
            'user_id': self.env.user.id,
            'model_id': self.env.ref('mail.model_mail_thread_cc').id,
            'domain': [("id", ">=", 1)],
        }
        with self.assertRaises(UserError) as validation:
            self.env['marketing.filter'].sudo().create(vals)
        self.assertEqual(
            validation.exception.args[0],
            'The filter domain is not valid for this target model.')
