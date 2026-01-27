# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import common


class TestDocumentRequestTemplate(common.TransactionCase):
    """Test class for document.request.template related methods."""

    def test_get_managers(self):
        """Test getting managers."""
        manager = self.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'testmanager',
        })
        manager.write({'groups_id': [fields.Command.link(self.env.ref('cyllo_documents.group_cyllo_documents_manager').id)]})
        document_request = self.env['document.request.template'].create({
            'name': 'Test Template',
            'manager_id': manager.id,
        })
        document_request._get_managers()
        self.assertIn(manager.id, document_request.user_ids.ids)
