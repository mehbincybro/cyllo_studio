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
from odoo import fields

class TestSocialMediaPost(TransactionCase):

    def setUp(self):
        super(TestSocialMediaPost, self).setUp()
        self.post = self.env['social.media.post'].create({
            'name': 'Test Post',
            'description': 'Test Content',
            'company_id': self.env.company.id,
            'user_id': self.env.user.id
        })

    def test_initial_state(self):
        self.assertEqual(self.post.state, 'draft')
        self.assertEqual(self.post.mode, 'url')

    def test_action_post(self):
        self.post.action_post()
        self.assertEqual(self.post.state, 'post')
        self.assertTrue(self.post.posted_date)

    def test_compute_feed_count(self):
        # Create feeds linked to this post
        self.env['social.media.feed'].create({
            'post_id': self.post.id,
            'description': 'Feed 1',
            'company_id': self.env.company.id
        })
        self.env['social.media.feed'].create({
            'post_id': self.post.id,
            'description': 'Feed 2',
            'company_id': self.env.company.id
        })
        
        # Trigger compute
        self.post._compute_feed_count()
        # compute field might need invalidation or immediate read
        self.assertEqual(int(self.post.feed_count), 2)

    def test_onchange_mode(self):
        self.post.mode = 'content_only'
        self.post._onchange_mode()
        # If no error, pass.

    def test_action_open_feed(self):
        action = self.post.action_open_feed()
        self.assertEqual(action['res_model'], 'social.media.feed')
        self.assertEqual(action['domain'], [('post_id', '=', self.post.id)])
