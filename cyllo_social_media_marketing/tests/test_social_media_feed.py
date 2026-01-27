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
from odoo.tests.common import TransactionCase
from unittest.mock import MagicMock, patch


class TestSocialMediaFeed(TransactionCase):

    def setUp(self):
        super(TestSocialMediaFeed, self).setUp()
        self.fb_account = self.env['social.fb.account'].create({
            'facebook_page_name': 'FB Page',
            'state': 'connected',
            'facebook_access_token': 'token',
            'facebook_user_access_token': 'token',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        })

        self.insta_account = self.env['social.insta.account'].create({
            'facebook_insta_page_name': 'Insta Page',
            'state': 'connected',
            'instagram_access_token': 'token',
            'instagram_page_access_token': 'token',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        })

    def test_get_dashboard_data(self):
        """Test fetching dashboard data aggregation without invalid domain crash"""

        FakeFeed = MagicMock()

        # Fake feed records returned by search()
        fb_feed = MagicMock(
            fb_account_id=self.fb_account,
            ig_account_id=False,
            likes_count=10,
            comments_count=5,
        )

        ig_feed = MagicMock(
            fb_account_id=False,
            ig_account_id=self.insta_account,
            likes_count=20,
            comments_count=8,
        )

        FakeFeed.__iter__.return_value = [fb_feed, ig_feed]

        with patch(
                'odoo.addons.cyllo_social_media_marketing.models.social_media_feed.SocialMediaFeed.search',
                return_value=FakeFeed
        ):
            result = self.env['social.media.feed'].get_dashboard_data()

        self.assertTrue(result)
        self.assertIn('dashboard_data', result)

        data = result['dashboard_data']
        self.assertTrue(data)

        fb_data = next(
            (d for d in data if d['platform'] == 'social.fb.account'), None
        )
        self.assertIsNotNone(fb_data)
        self.assertEqual(fb_data['account_name'], 'FB Page')

        ig_data = next(
            (d for d in data if d['platform'] == 'social.insta.account'), None
        )
        self.assertIsNotNone(ig_data)
        self.assertEqual(ig_data['account_name'], 'Insta Page')

    @patch(
        'odoo.addons.cyllo_social_media_marketing.models.social_fb_account.SocialFbAccount.action_connect')
    def test_action_create_connect_fb(self, mock_connect):
        """Test creating and connecting FB account via feed model helper"""
        data = {
            'facebook_page_name': 'New FB',
            'facebook_access_token': 't',
            'facebook_user_access_token': 't',
            'meta_app_number': '1',
            'meta_app_secret': '1',
            'company_id': self.env.company.id
        }

        # We need to mock action_connect on the instance created.
        # Since action_create_connect calls `account.action_connect()`, the patch above on the class might work if method is standard.

        self.env['social.media.feed'].action_create_connect(data,
                                                            'social.fb.account')
        mock_connect.assert_called_once()

        account = self.env['social.fb.account'].search(
            [('facebook_page_name', '=', 'New FB')])
        self.assertTrue(account)

    def test_get_model(self):
        """Test get_model method with mocked menu lookup"""

        fake_menu = MagicMock()
        fake_menu.id = 1

        def menu_search_side_effect(domain, limit=1):
            # domain usually contains something like ('name', 'ilike', 'Facebook')
            domain_str = str(domain)

            if 'Facebook' in domain_str:
                return fake_menu
            if 'Instagram' in domain_str:
                return fake_menu

            return False

        with patch('odoo.models.Model.search',
                   side_effect=menu_search_side_effect):

            res_fb = self.env['social.media.feed'].get_model(
                'social.fb.account')
            self.assertTrue(res_fb)

            res_ig = self.env['social.media.feed'].get_model(
                'social.insta.account')
            self.assertTrue(res_ig)

            res_yt = self.env['social.media.feed'].get_model('youtube.account')
            self.assertFalse(res_yt)
