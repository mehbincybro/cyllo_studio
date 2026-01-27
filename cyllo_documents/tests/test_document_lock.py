# -*- coding: utf-8 -*-
import os

from odoo import fields
from odoo.tests import common


class TestDocumentLock(common.TransactionCase):
    """Test class for document.lock related methods."""

    @classmethod
    def setUpClass(cls):
        """Set up initial data for test cases."""
        super().setUpClass()
        with open(os.path.dirname(__file__) + '/test.jpg', 'rb') as file:
            cls.file_data_content = file.read()
        cls.workspace_id = cls.env['document.workspace'].create({
            'name': 'Test Workspace',
        })
        cls.document_id = cls.env['document.file'].create({
            'name': 'Test Document',
            'workspace_id': cls.workspace_id.id,
            'active': True,
        })
        cls.document_lock = cls.env['document.lock'].create({
            'document_file_id': cls.document_id.id,
            'password': 'test123',
        })

    def test_lock_doc(self):
        """Test locking a document."""
        result = self.document_lock.lock_doc()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.env.user.write(
            {'groups_id': [fields.Command.link(self.env.ref('cyllo_documents.group_cyllo_documents_manager').id)]})
        self.document_lock.lock_doc()
        self.assertTrue(self.document_lock.is_lock)

    def test_unlock_doc(self):
        """Test unlocking a document."""
        result = self.document_lock.unlock_doc()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.unlock_doc()
        self.assertFalse(self.document_id.is_locked)

    def test_document_share(self):
        """Test sharing a document."""
        result = self.document_lock.document_share()
        self.assertTrue(result['type'], 'ir.actions.client')

    def test_document_download(self):
        """Test downloading a document."""
        result = self.document_lock.document_download()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.env.context = {'document_url': 'www.google.com'}
        result = self.document_lock.document_download()
        self.assertTrue(result['type'], 'ir.actions.act_url')

    def test_document_create_lead(self):
        """Test document creation for leads."""
        result = self.document_lock.document_create_lead()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.document_create_lead()
        self.assertTrue(
            self.document_id.action_btn_create_lead(self.document_id.id))

    def test_document_create_task(self):
        """Test document creation for tasks."""
        result = self.document_lock.document_create_task()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.document_create_task()
        self.assertTrue(
            self.document_id.action_btn_create_task(self.document_id.id))

    def test_document_lock_mail(self):
        """Test document locking via mail."""
        result = self.document_lock.document_lock_mail()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        result = self.document_lock.document_lock_mail()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'Sent document')

    def test_document_copy_mail(self):
        """Test document copying via mail."""
        result = self.document_lock.document_copy_mail()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        result = self.document_lock.document_copy_mail()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['name'], 'copy')

    def test_document_lock_archive(self):
        """Test document locking in the archive."""
        result = self.document_lock.document_copy_mail()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.document_copy_mail()
        self.assertTrue(self.document_id.active)

    def test_document_move_to_trash(self):
        """Test moving a document to the trash."""
        result = self.document_lock.document_move_to_trash()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.document_copy_mail()
        self.assertTrue(self.document_id.exists())

    def test_document_delete_permanent(self):
        """Test permanent document deletion."""
        result = self.document_lock.document_move_to_trash()
        self.assertTrue(result['type'], 'ir.actions.client')
        self.document_lock.is_lock = True
        self.document_lock.document_copy_mail()
        self.assertTrue(self.document_id.exists())
