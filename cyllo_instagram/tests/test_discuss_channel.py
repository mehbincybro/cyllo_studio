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
from types import SimpleNamespace
from unittest.mock import patch, PropertyMock

from odoo.tests.common import TransactionCase


class TestDiscussChannelInstagram(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ------------------------------------------------------------
        # Create Instagram chat partner
        # ------------------------------------------------------------
        cls.insta_partner = cls.env["res.partner"].create({
            "name": "Instagram Partner",
        })

        # ------------------------------------------------------------
        # Create discuss channel
        # ------------------------------------------------------------
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Instagram Test Channel",
            "channel_partner_ids": [
                (4, cls.env.user.partner_id.id),
                (4, cls.insta_partner.id),
            ],
            "insta_partner_number": "1234567890",
        })

    # ==============================================================
    # TEST: action_find_partner_insta
    # ==============================================================

    def test_action_find_partner_insta(self):
        result = self.channel.action_find_partner_insta()

        self.assertEqual(result["partner"].id, self.insta_partner.id)
        self.assertEqual(result["instagram"], "1234567890")

    # ==============================================================
    # TEST: action_message_chat_discuss_insta
    # ==============================================================

    @patch(
        "odoo.addons.cyllo_instagram.models.discuss_channel.requests.post"
    )
    def test_action_message_chat_discuss_insta(self, mock_post):

        # ------------------------------------------------------------
        # Mock Instagram account object
        # ------------------------------------------------------------
        fake_account = SimpleNamespace(
            instagram_base_url="https://graph.facebook.com/v19.0",
            instagram_page_access_token="TEST_ACCESS_TOKEN",
        )

        # ------------------------------------------------------------
        # Patch insta_account_id relation
        # ------------------------------------------------------------
        with patch.object(
            type(self.insta_partner),
            "insta_account_id",
            new_callable=PropertyMock,
            return_value=fake_account,
        ):
            response = self.channel.action_message_chat_discuss_insta(
                "Hello from test case"
            )

        # ------------------------------------------------------------
        # ASSERT: HTTP call
        # ------------------------------------------------------------
        self.assertEqual(mock_post.call_count, 1)

        args, kwargs = mock_post.call_args

        self.assertIn(
            "/me/messages?access_token=TEST_ACCESS_TOKEN",
            args[0],
        )
        self.assertEqual(
            kwargs["json"]["recipient"]["id"],
            "1234567890",
        )
        self.assertEqual(
            kwargs["json"]["message"]["text"],
            "Hello from test case",
        )

        # ------------------------------------------------------------
        # ASSERT: UI response
        # ------------------------------------------------------------
        self.assertEqual(response["type"], "ir.actions.client")
        self.assertEqual(response["tag"], "display_notification")
        self.assertEqual(response["params"]["type"], "success")
