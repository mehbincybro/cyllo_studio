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
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from odoo.tests import common

class TestSocialMediaPost(common.TransactionCase):
    """
    Test cases for 'social.media.post' model, covering video publication,
    onchange logic, and wizard-based uploads.
    """

    def setUp(self):
        """
        Setup test data for social media posts, including accounts and channels.
        """
        super().setUp()

        self.youtube_account = self.env['youtube.account'].create({
            'name': 'Test Account',
            'client_number': 'test_client',
            'client_secret': 'test_secret',
            'state': 'sync',
            'access_token': 'test_token',
            'refresh_token': 'test_refresh_token',
            'token_expiry_date': datetime.now() + timedelta(hours=1),
        })

        self.youtube_channel = self.env['youtube.channel'].create({
            'name': 'Test Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_123',
            'youtube_etag': 'etag_123',
            'customUrl': 'custom_url',
            'is_active': True,
        })

        self.social_post = self.env['social.media.post'].create({
            'name': 'Test Post',
            'description': 'Test Description',
            'post_on_youtube': True,
            'youtube_channel_id': self.youtube_channel.id,
            'mode': 'upload',
        })

    def test_social_media_post_creation(self):
        """
        Test the creation and field initialization of a social media post.
        """
        self.assertEqual(self.social_post.name, 'Test Post')
        self.assertTrue(self.social_post.post_on_youtube)
        self.assertEqual(self.social_post.mode, 'upload')
        self.assertEqual(self.social_post.youtube_channel_id, self.youtube_channel)

    def test_youtube_video_number_assignment(self):
        """
        Test the manual assignment of a YouTube video identifier.
        """
        self.social_post.youtube_video_number = 'assigned_video_123'
        self.assertEqual(self.social_post.youtube_video_number, 'assigned_video_123')

    def test_youtube_channel_relationship(self):
        """
        Test switching the target YouTube channel for a post.
        """
        self.assertEqual(self.social_post.youtube_channel_id, self.youtube_channel)

        channel2 = self.env['youtube.channel'].create({
            'name': 'Second Channel',
            'youtube_account_id': self.youtube_account.id,
            'youtube_number': 'channel_456',
            'youtube_etag': 'etag_456',
            'customUrl': 'custom_url_2',
            'is_active': True,
        })

        self.social_post.youtube_channel_id = channel2
        self.assertEqual(self.social_post.youtube_channel_id, channel2)

    def test_mode_default_value(self):
        """
        Test the default value of the publication mode field.
        """
        post = self.env['social.media.post'].create({
            'name': 'Test Post 2',
            'description': 'Test',
        })
        self.assertIn(post.mode, ['url', 'upload'])

    def test_onchange_post_on_youtube(self):
        """
        Test the onchange logic when enabling YouTube publication.
        """
        self.social_post.post_on_youtube = True
        self.social_post._onchange_post_on_youtube()

    def test_onchange_mode_upload(self):
        """
        Test formatting resets when switching to 'upload' mode.
        """
        self.social_post.mode = 'upload'
        self.social_post._onchange_mode()

    def test_onchange_mode_not_upload(self):
        """
        Test state resets when switching away from 'upload' mode.
        """
        self.social_post.mode = 'url'
        self.social_post._onchange_mode()
        self.assertFalse(self.social_post.post_on_youtube)

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_draft_state(self, mock_put):
        """
        Test that posting a record without a video number triggers a warning.
        """
        self.social_post.youtube_video_number = None
        result = self.social_post.action_post()
        self.assertEqual(result['params']['type'], 'warning')

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_success(self, mock_put):
        """
        Test successful synchronization of a recorded post with YouTube.
        """
        self.social_post.write({
            'youtube_video_number': 'video_123',
            'state': 'post',
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'video_123',
            'snippet': {'title': 'Test Post', 'channelId': 'channel_123', 'thumbnails': {}}
        }
        mock_put.return_value = mock_response

        self.social_post.action_post()
        feed = self.env['social.media.feed'].search([('youtube_post_id', '=', self.social_post.id)])
        self.assertTrue(feed.exists())

    @patch('odoo.addons.cyllo_youtube.models.social_media_post.requests.put')
    def test_action_post_api_error(self, mock_put):
        """
        Test behavior when the YouTube API returns an error during publication.
        """
        self.social_post.write({
            'youtube_video_number': 'video_123',
            'state': 'post',
        })

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_put.return_value = mock_response

        result = self.social_post.action_post()
        self.assertEqual(result['params']['type'], 'warning')

    @patch('odoo.addons.cyllo_youtube.models.youtube_account.requests.post')
    def test_action_upload_video_new(self, mock_post):
        """
        Test launching the video upload wizard for a new post.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'access_token': 'new_token', 'expires_in': 3600}
        mock_post.return_value = mock_response

        result = self.social_post.action_upload_video()
        self.assertEqual(result['res_model'], 'upload.video.wizard')

    @patch('odoo.addons.cyllo_youtube.models.youtube_account.requests.post')
    def test_action_upload_video_existing(self, mock_post):
        """
        Test reopening an existing upload wizard record.
        """
        wizard = self.env['upload.video.wizard'].create({'youtube_post_id': self.social_post.id})
        result = self.social_post.action_upload_video()
        self.assertEqual(result['res_id'], wizard.id)

    def test_get_youtube_account(self):
        """
        Test retrieving the active YouTube account credentials for the post.
        """
        result = self.social_post.get_youtube_account()
        self.assertEqual(result['key'], self.youtube_account.access_token)
