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
from unittest.mock import patch, Mock
from odoo.tests.common import TransactionCase

class TestSocialMediaFeedInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.insta_account = cls.env["social.insta.account"].create({
            "instagram_account_number": "123",
            "instagram_business_account_number": "123",
            "instagram_access_token": "TEST_ACCESS_TOKEN",
            "instagram_page_access_token": "TEST_PAGE_ACCESS_TOKEN",
            "facebook_insta_page_name": "Test Page",
            "meta_app_number": "META_APP_ID",
            "meta_app_secret": "META_APP_SECRET",
            "instagram_base_url": "https://graph.facebook.com/v19.0",
            "state": "connected",
        })

        cls.feed = cls.env["social.media.feed"].create({
            "ig_media_number": "MEDIA_123",
            "posted_on_ig": True,
            "ig_account_id": cls.insta_account.id,
        })

    @patch("odoo.addons.cyllo_instagram.models.social_media_feed.SocialMediaFeed.get_ig_comments_data")
    def test_action_fetch_data_from_ig_feed_creates_partner(self, mock_comments):
        """
        Test partner creation when a new Instagram user is found.
        """

        # Mock get_ig_comments_data to return comment data
        mock_comments.return_value = {
            "comments": {
                "data": [{"id": "COMMENT_1"}]
            }
        }

        # Patch requests.get to return user details
        with patch("odoo.addons.cyllo_instagram.models.social_media_feed.requests.get") as mock_get:
            # First call: comment details
            # Second call: user details
            mock_get.side_effect = [
                Mock(json=Mock(return_value={"from": {"id": "USER_1"}})),
                Mock(json=Mock(return_value={"id": "USER_1", "name": "Instagram User"})),
            ]

            result = self.feed.action_fetch_data_from_ig_feed()

        partner = self.env["res.partner"].search([("unique_ig_number", "=", "USER_1")])
        self.assertTrue(partner, "Partner was not created!")
        self.assertEqual(partner.name, "Instagram User")
        self.assertEqual(partner.insta_account_id.id, self.insta_account.id)
        self.assertEqual(partner.feed_id.id, self.feed.id)

        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["params"]["type"], "success")
        self.assertIn("new contact saved", result["params"]["message"])

    @patch("odoo.addons.cyllo_instagram.models.social_media_feed.SocialMediaFeed.get_ig_comments_data")
    def test_action_fetch_data_from_ig_feed_no_new_partner(self, mock_comments):
        """
        Test scenario when all partners already exist.
        """

        # Pre-create partner
        self.env["res.partner"].create({
            "name": "Instagram User",
            "unique_ig_number": "USER_1",
            "insta_account_id": self.insta_account.id,
            "feed_id": self.feed.id,
        })

        # Mock get_ig_comments_data to return comment data
        mock_comments.return_value = {
            "comments": {
                "data": [{"id": "COMMENT_1"}]
            }
        }

        # Patch requests.get to return same user details
        with patch("odoo.addons.cyllo_instagram.models.social_media_feed.requests.get") as mock_get:
            mock_get.side_effect = [
                Mock(json=Mock(return_value={"from": {"id": "USER_1"}})),
                Mock(json=Mock(return_value={"id": "USER_1", "name": "Instagram User"})),
            ]

            result = self.feed.action_fetch_data_from_ig_feed()

        self.assertEqual(result["params"]["type"], "warning")
        self.assertIn("No new contacts", result["params"]["message"])
