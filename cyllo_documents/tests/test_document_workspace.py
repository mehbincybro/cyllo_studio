# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests import common


class TestDocumentWorkspace(common.TransactionCase):
    """Test methods of the Workspace"""

    @classmethod
    def setUpClass(cls):
        """Set up class values"""
        super().setUpClass()
        cls.workspace = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
            'privacy_visibility': 'followers'
        })

    def test_button_view_document(self):
        """Test the view document button."""
        result = self.workspace.button_view_document()
        self.assertEqual(result['res_model'], 'document.file')
        self.assertEqual(result['view_mode'], 'kanban,form')

    def test__compute_document_count(self):
        """Test computation of the document count."""
        self.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': self.workspace.id
        })
        self.workspace._compute_document_count()
        self.assertEqual(self.workspace.document_count, 1)

    def test_work_spaces(self):
        """Test workspace search function."""
        result = self.workspace.work_spaces()
        self.assertTrue(
            any(record['name'] == self.workspace.name for record in result))

    def test_write(self):
        """Test the workspace write operation."""
        with patch('odoo.models.Model.env') as mock_env:
            mock_google_connector = mock_env['google.drive.connector']
            mock_one_drive_connector = mock_env['one.drive.connector']
            mock_google_connector_obj = mock_google_connector.search.return_value
            mock_google_connector_obj.google_drive_token_validity = '2023-12-31'
            mock_one_drive_connector_obj = mock_one_drive_connector.search.return_value
            mock_one_drive_connector_obj.one_drive_token_validity = '2023-12-31'
            updated_vals = {'name': 'New Workspace'}
            with patch('odoo.models.Model.write') as mock_write:
                self.workspace.write(updated_vals)
                mock_write.assert_called_once_with(updated_vals)
