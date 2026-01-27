# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import base64
from io import BytesIO
from PIL import Image
from odoo.tests.common import TransactionCase
from unittest.mock import patch, Mock
from odoo.exceptions import ValidationError

class TestSocialMediaPostInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a fake Instagram account with all required fields
        cls.insta_account = cls.env['social.insta.account'].create({
            'instagram_base_url': 'https://graph.facebook.com/v17.0',
            'facebook_insta_page_number': '123456789',
            'facebook_insta_page_name': 'Fake Page',
            'instagram_access_token': 'fake_token',
            'instagram_page_access_token': 'fake_page_token',
            'meta_app_number': '987654321',
            'meta_app_secret': 'fake_secret',
            'state': 'not connected',
            'company_id': cls.env.company.id
        })

        # Dynamically generate a minimal 1x1 JPEG image for the attachment
        img = Image.new('RGB', (1, 1), color='white')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_base64 = base64.b64encode(buffer.getvalue())

        # Create a valid attachment with the generated image
        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'test.jpg',
            'mimetype': 'image/jpeg',
            'datas': img_base64,
            'public': False
        })

        # Create a social media post with the required 'name' field
        cls.post = cls.env['social.media.post'].create({
            'name': 'Test Instagram Post',  # required by Odoo
            'description': 'Test Instagram Post',
            'post_on_instagram': True,
            'insta_account_ids': [(6, 0, [cls.insta_account.id])],
            'ir_attachment_ids': [(6, 0, [cls.attachment.id])],
            'mode': 'attachment',
            'company_id': cls.env.company.id,
        })

    @patch('requests.get')
    @patch('requests.post')
    def test_action_post_success(self, mock_post, mock_get):
        """
        Test posting a social media post to Instagram successfully.
        """

        # Mock GET request for business account ID and profile details
        mock_get.side_effect = [
            Mock(json=Mock(return_value={'instagram_business_account': {'id': '987654321'}})),
            Mock(json=Mock(return_value={'username': 'fakeuser', 'name': 'Fake User'}))
        ]

        # Mock POST requests for media creation and publishing
        def post_side_effect(url, data):
            if 'media_publish' in url:
                mock_resp = Mock()
                mock_resp.text = '{"id": "published123"}'
                return mock_resp
            return Mock(text='{"id": "media123"}')

        mock_post.side_effect = post_side_effect

        # Call action_post
        self.post.action_post()

        # Assert a social media feed was created
        feed = self.env['social.media.feed'].search([('post_id', '=', self.post.id)], limit=1)
        self.assertTrue(feed)
        self.assertEqual(feed.ig_media_number, 'published123')
        self.assertEqual(feed.posted_image_url, self.attachment.public_url)
