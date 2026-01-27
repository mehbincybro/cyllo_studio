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

class TestIrActionsServerApproval(TransactionCase):
    """Test server actions with approval rules in cyllo_approval module."""

    def setUp(self):
        super().setUp()
        if 'crm.lead' not in self.env:
            self.skipTest("CRM module not installed")

        # Create test user
        self.user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test_user@example.com'
        })

        # Create a CRM Lead as test record
        self.test_record = self.env['crm.lead'].with_user(self.user).create({
            'name': 'Test Lead for Server Action'
        })

        # Create server action
        self.server_action = self.env['ir.actions.server'].create({
            'name': 'Test Server Action',
            'model_id': self.env['ir.model']._get('crm.lead').id,
            'state': 'code',
            'code': 'action = True',  # simple code for test
        })

        # Create approval rule linked to server action
        self.approval_rule = self.env['approval.rule'].create({
            'name': 'Server Action Rule',
            'definition_type': 'server_action',
            'state': 'enable',
            'model_select': 'crm.lead',
            'server_action_id': self.server_action.id,
            'user_type': 'user',
            'user_id': self.user.id,
        })

    def test_run_without_approval(self):
        """If no approval exists, should return a warning or bool from super().run()"""
        ctx = {'active_model': 'crm.lead', 'active_id': self.test_record.id}
        result = self.server_action.with_user(self.user).with_context(ctx).run()

        if isinstance(result, dict):
            self.assertEqual(result['type'], 'ir.actions.client')
            self.assertEqual(result['params']['type'], 'warning')
            self.assertIn('Need an Approval', result['params']['message'])
        else:
            self.assertTrue(result)

    def test_run_with_approved_request(self):
        """If an approved request exists, server action should run normally"""
        # Create approved approval request (no res_model field)
        self.env['approval.request'].create({
            'approval_rule_id': self.approval_rule.id,
            'res_id': self.test_record.id,
            'state': 'approved',
            'requested_by_id': self.user.id,
        })

        ctx = {'active_model': 'crm.lead', 'active_id': self.test_record.id}
        result = self.server_action.with_user(self.user).with_context(ctx).run()

        # The server action code returns True in test
        self.assertTrue(result)

    def test_run_without_active_model(self):
        """If active_model is missing in context, should fallback to normal server action"""
        result = self.server_action.with_user(self.user).with_context({}).run()
        self.assertTrue(result)
