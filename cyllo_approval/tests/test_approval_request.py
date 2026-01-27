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
from odoo.exceptions import AccessError


class TestApprovalRequest(TransactionCase):

    def setUp(self):
        super().setUp()

        # Users
        self.requester = self.env['res.users'].create({
            'name': 'Requester',
            'login': 'req_ar',
            'email': 'req@test.com',
        })
        self.approver = self.env['res.users'].create({
            'name': 'Approver',
            'login': 'app_ar',
            'email': 'app@test.com',
        })

        # Approval rule
        self.rule = self.env['approval.rule'].create({
            'name': 'Approval Rule',
            'user_type': 'user',
            'user_id': self.approver.id,
            'definition_type': 'domain',
            'domain': '[]',
            'email_notification': False,
        })

        # Approval request (IMPORTANT: pass context)
        self.request = self.env['approval.request'].with_context(
            default_approval_rule_id=self.rule.id
        ).create({
            'approval_rule_id': self.rule.id,
            'requested_by_id': self.requester.id,
        })

    # --------------------------------------------------
    # Creation & defaults
    # --------------------------------------------------

    def test_01_request_created(self):
        """Approval request should be created successfully"""
        self.assertTrue(self.request)
        self.assertEqual(self.request.state, 'pending')
        self.assertEqual(self.request.company_id, self.env.company)

    def test_02_default_approver_set(self):
        """Approver should be populated from rule via context"""
        self.assertIn(self.approver, self.request.approver_ids)

    # --------------------------------------------------
    # State changes
    # --------------------------------------------------

    def test_03_write_state_approved(self):
        """State should change to approved"""
        self.request.write({'state': 'approved'})
        self.assertEqual(self.request.state, 'approved')

    def test_04_write_state_rejected(self):
        """State should change to rejected"""
        self.request.write({'state': 'rejected'})
        self.assertEqual(self.request.state, 'rejected')

    # --------------------------------------------------
    # Mark as read
    # --------------------------------------------------

    def test_05_mark_as_read(self):
        """Approver should be added to read_by_ids even without write access"""
        self.request.with_user(self.approver).mark_as_read()
        self.assertIn(self.approver, self.request.read_by_ids)

    # --------------------------------------------------
    # Action forward
    # --------------------------------------------------

    def test_06_action_forward(self):
        """Forward action should return correct window action"""
        action = self.request.action_forward()

        self.assertEqual(action['res_model'], 'approval.forward')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(
            action['context']['default_approval_request_id'],
            self.request.id
        )
        self.assertEqual(
            action['context']['default_from_user_ids'],
            self.request.approver_ids.ids
        )

    # --------------------------------------------------
    # Helper methods
    # --------------------------------------------------

    def test_07_get_approvers_emails(self):
        """Should return comma-separated approver emails"""
        emails = self.request._get_approvers_emails()
        self.assertIn(self.approver.email, emails)

    # --------------------------------------------------
    # Access rules
    # --------------------------------------------------

    def test_08_unauthorized_read_access(self):
        """Random user should not read approval request"""
        other_user = self.env['res.users'].create({
            'name': 'Other',
            'login': 'other_ar',
        })

        with self.assertRaises(AccessError):
            self.request.with_user(other_user).read(['id'])
