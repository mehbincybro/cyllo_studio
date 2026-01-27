# -*- coding: utf-8 -*-
import logging
from odoo.tests import common

_LOGGER = logging.getLogger(__name__)


class TestDocumentTrash(common.TransactionCase):

    def test_action_restore_document(self):
        """Test for the fields in 'document.trash''"""
        _LOGGER.info("Starts 'action_restore_document' functiontest")
        workspace_id = self.env.ref(
            "cyllo_document_spreadsheet.document_workspace_spreadsheet").id
        self.trash = self.env['document.trash'].create({
            'name': "Event Management Report.xlsx",
            'workspace_id': workspace_id,
            'brochure_url': "http://test:8017/web/image/1352?unique=82"
                            "5387c05d27cd359e3dd76247fbf0dc08a0ae9f",
        })
        result = self.trash.action_restore_document()
        self.assertEqual(result['name'], 'Trash')
        self.assertEqual(result['target'], 'main')
        self.assertEqual(result['view_mode'], 'tree,form')
        self.assertEqual(result['res_model'], 'document.trash')
        self.assertEqual(result['type'], 'ir.actions.act_window')
        _LOGGER.info("End 'action_restore_document' function test")
