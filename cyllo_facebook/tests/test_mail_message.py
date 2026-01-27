from unittest.mock import patch, Mock
from odoo.tests.common import TransactionCase

class TestMailMessageFacebook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fb_account = cls.env['social.fb.account'].create({
            'facebook_page_name': 'Test Facebook Page',
            'facebook_access_token': 'page_test_token',
            'facebook_user_access_token': 'user_test_token',
            'facebook_base_url': 'https://graph.facebook.com/v18.0',
            'state': 'connected',
            'meta_app_number': 'test_meta_app_001',
            'meta_app_secret': 'test_meta_app_secret',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Facebook User',
            'email': 'fbuser@test.com',
            'fb_account_id': cls.fb_account.id,
        })
        cls.lead = cls.env['crm.lead'].create({
            'name': 'FB Lead',
            'type': 'lead',
            'partner_id': cls.partner.id,
        })
        cls.message = cls.env['mail.message'].create({
            'author_id': cls.partner.id,
            'email_from': cls.partner.email,
            'preview': 'Test FB Message',
            'is_from_fb': True,
            'fb_sender_number': '123456',
            'model': 'crm.lead',
            'res_id': cls.lead.id,
        })

