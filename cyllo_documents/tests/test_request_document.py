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
from odoo.tests import common


class TestRequestDocument(common.TransactionCase):
    """Test class for request.document related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document = cls.env['request.document'].create({
            'user_id': cls.env.user.id,
            'needed_doc': 'Document XYZ',
            'workspace_id': cls.workspace_id.id
        })

    def test_action_send_document_request(self):
        """ Test the 'action_send_document_request' method.
            Verifies if a document request email is sent correctly."""
        self.document.user_id = self.env.user.id
        # Call the method to send the document request
        self.document.action_send_document_request()
        # Assert that a mail object is created and sent successfully
        sent_mail = self.env['mail.mail'].sudo().search(
            [('subject', '=', 'Document Request')])
        self.assertTrue(sent_mail, "Mail should be sent")
        self.assertEqual(sent_mail.subject, 'Document Request',
                         "Subject should match")
        self.assertEqual(sent_mail.email_to, self.env.user.partner_id.email,
                         "Recipient should match")

    def test_get_request(self):
        """Test the 'get_request' method."""
        requests = self.document.get_request()
        self.assertEqual(requests[0]['needed_doc'], 'Document XYZ')
        self.assertEqual(requests[0]['workspace'], 'Test Workspace')
