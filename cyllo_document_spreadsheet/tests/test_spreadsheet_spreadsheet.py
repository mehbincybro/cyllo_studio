# -*- coding: utf-8 -*-
import logging
from odoo.tests import common

_LOGGER = logging.getLogger(__name__)


class TestDocumentTrash(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to declare data in as variable. """
        super().setUpClass()
        cls.workspace_id = cls.env.ref(
            "cyllo_document_spreadsheet.document_workspace_spreadsheet").id
        cls.document = cls.env['document.file'].create({
            'workspace_id': cls.workspace_id,
            'is_excel': False,
        })
        cls.spreadsheet_id = cls.env['spreadsheet.spreadsheet'].create({
            'name': 'Test name',
            'document_file_id': cls.document.id,
            'is_document': True,
        })

    def test_create(self):
        """Check the 'create' fn return values """
        _LOGGER.info("Starts test for 'create' fn")
        vals = [{'name': 'Test name', 'document_file_id': self.document.id,
                 'is_document': True}]
        self.spreadsheet_id.document_file_id = False
        spreadsheet_id = self.spreadsheet_id.create(vals)
        self.assertEqual(spreadsheet_id.name, 'Test name')
        self.assertEqual(spreadsheet_id.document_file_id.id, self.document.id)
        self.assertEqual(spreadsheet_id.is_document, True)
        _LOGGER.info("End test for 'create' fn")
