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
from odoo.exceptions import ValidationError


class TestApprovalRule(TransactionCase):

    def setUp(self):
        super().setUp()

        # Users
        self.user_1 = self.env['res.users'].create({
            'name': 'Approver User',
            'login': 'approver_rule',
            'email': 'approver@rule.com',
        })

        self.user_2 = self.env['res.users'].create({
            'name': 'Second User',
            'login': 'second_rule',
            'email': 'second@rule.com',
        })

        # Group
        self.group = self.env['res.groups'].create({
            'name': 'Approval Group',
            'users': [(6, 0, [self.user_1.id, self.user_2.id])]
        })

    # --------------------------------------------------
    # Creation
    # --------------------------------------------------

    def test_01_create_rule_user_type_user(self):
        """Rule should be created with user approver"""
        rule = self.env['approval.rule'].create({
            'name': 'User Based Rule',
            'user_type': 'user',
            'user_id': self.user_1.id,
            'definition_type': 'domain',
            'domain': '[]',
        })

        self.assertTrue(rule)
        self.assertEqual(rule.user_type, 'user')
        self.assertEqual(rule.user_id, self.user_1)

    def test_02_create_rule_user_type_group(self):
        """Rule should be created with group approvers"""
        rule = self.env['approval.rule'].create({
            'name': 'Group Based Rule',
            'user_type': 'group',
            'group_id': self.group.id,
            'definition_type': 'domain',
            'domain': '[]',
        })

        self.assertTrue(rule)
        self.assertEqual(rule.user_type, 'group')
        self.assertEqual(rule.group_id, self.group)

    # --------------------------------------------------
    # Onchange logic
    # --------------------------------------------------

    def test_03_onchange_user_type_user(self):
        """Group and related fields should reset when user_type = user"""
        rule = self.env['approval.rule'].new({
            'user_type': 'user',
            'group_id': self.group.id,
        })

        rule._onchange_user_type()
        self.assertFalse(rule.group_id)
        self.assertFalse(rule.related_user_id)

    def test_04_onchange_user_type_group(self):
        """User and related fields should reset when user_type = group"""
        rule = self.env['approval.rule'].new({
            'user_type': 'group',
            'user_id': self.user_1.id,
        })

        rule._onchange_user_type()
        self.assertFalse(rule.user_id)
        self.assertFalse(rule.related_user_id)

    # --------------------------------------------------
    # Domain handling
    # --------------------------------------------------

    def test_05_domain_parsing(self):
        """_domain should return evaluated domain"""
        rule = self.env['approval.rule'].create({
            'name': 'Domain Rule',
            'user_type': 'user',
            'user_id': self.user_1.id,
            'definition_type': 'domain',
            'domain': "[('id', '!=', 0)]",
        })

        domain = rule._domain()
        self.assertIsInstance(domain, list)
        self.assertEqual(domain[0][0], 'id')

    # --------------------------------------------------
    # State actions
    # --------------------------------------------------

    def test_06_action_enable(self):
        """Rule should move to enable state"""
        rule = self.env['approval.rule'].create({
            'name': 'Enable Rule',
            'user_type': 'user',
            'user_id': self.user_1.id,
            'definition_type': 'domain',
            'domain': '[]',
        })

        rule.action_enable()
        self.assertEqual(rule.state, 'enable')

    def test_07_action_disable(self):
        """Rule should move to disable state"""
        rule = self.env['approval.rule'].create({
            'name': 'Disable Rule',
            'user_type': 'user',
            'user_id': self.user_1.id,
            'definition_type': 'domain',
            'domain': '[]',
            'state': 'enable',
        })

        rule.action_disable()
        self.assertEqual(rule.state, 'disable')

    # --------------------------------------------------
    # Inherited model domain
    # --------------------------------------------------

    def test_08_get_inherited_models_domain(self):
        """_get_inherited_models should return a valid domain"""
        domain = self.env['approval.rule']._get_inherited_models()

        self.assertIsInstance(domain, list)
        self.assertEqual(domain[0][0], 'id')
        self.assertEqual(domain[0][1], 'in')
