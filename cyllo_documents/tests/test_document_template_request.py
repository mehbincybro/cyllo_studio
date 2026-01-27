# -*- coding: utf-8 -*-
from odoo.tests import common


class TestDocumentTemplateRequest(common.TransactionCase):
    """Test class for DocumentTemplateRequest methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for the tests."""
        super().setUpClass()
        cls.user = cls.env.user
        cls.employee = cls.env['hr.employee'].create({'name': 'Test Employee'})
        cls.document_template = cls.env['document.request.template'].create({
            'name': 'Test Document Template',
            'manager_id': cls.user.id,
        })
        cls.document_request = cls.env['document.template.request'].create({
            'document_id': cls.document_template.id,
            'employee_id': cls.employee.id,
            'user_id': cls.user.id,
        })

    def test_action_sent_document_approval(self):
        """Test action_sent_document_approval method."""
        self.document_request.action_sent_document_approval()
        self.assertEqual(self.document_request.state, 'document_approval')

    def test_action_approve(self):
        """Test action_approve method."""
        self.document_request.action_approve()
        self.assertEqual(self.document_request.state, 'approved')

    def test_action_preview_document(self):
        """Test action_preview_document method."""
        client_action = self.document_request.action_preview_document()
        self.assertEqual(client_action['type'], 'ir.actions.client')
        self.assertEqual(client_action['tag'], 'preview_document')

    def test_action_download_document(self):
        """Test action_download_document method."""
        report_action = self.document_request.action_download_document()
        self.assertTrue(report_action)

    def test_get_report_base_filename(self):
        """Test _get_report_base_filename method."""
        filename = self.document_request._get_report_base_filename()
        self.assertEqual(filename, self.document_template.name)
