# -*- coding: utf-8 -*-
from odoo.tests import common


class TestDocumentDeleteTrash(common.TransactionCase):
    """Test class for document.delete.trash related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for test cases."""
        super().setUpClass()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document = cls.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': cls.workspace_id.id
        })
        cls.delete_doc = cls.env['document.delete.trash'].create({
            'document_file_id': cls.document.id
        })

    def test_document_move_trash(self):
        """Test the 'document_move_trash' method.
        Validates the functionality of moving a document to the trash,
        testing both locked and unlocked states."""
        self.document.is_locked = True
        result = self.delete_doc.document_move_trash()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.document.is_locked = False
        result = self.delete_doc.document_move_trash()
        self.assertEqual(result, None)

    def test_document_permanent_delete(self):
        """Test the 'document_permanent_delete' method.
           Verifies the permanent deletion of a document from the trash,
           testing both locked and unlocked states."""
        self.document.is_locked = True
        result = self.delete_doc.document_permanent_delete()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Lock')
        self.document.is_locked = False
        result = self.delete_doc.document_permanent_delete()
        self.assertEqual(result, None)
