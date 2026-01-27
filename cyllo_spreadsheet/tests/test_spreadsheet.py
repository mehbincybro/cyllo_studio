# -*- coding: utf-8 -*-
import logging
from odoo import Command
from odoo.tests import common

_LOGGER = logging.getLogger(__name__)


class TestSpreadsheet(common.TransactionCase):
    """Test case suite for the Spreadsheet module."""
    _LOGGER.info("Testing bSpreadsheet")

    def test_spreadsheet_revision_fields(self):
        """Test the fields of the 'spreadsheet.cy.revision' model."""
        sheet_model = self.env['spreadsheet.cy.revision'].create({
            'model': 'Test Spreadsheet',
            'res_id': 14,
            'type': 'Test type',
            'client_id': 'Test Client',
            'server_revision_id': 'Test server revision',
            'next_revision_id': 'Test next revision',
            'commands': 'Test commands'
        })
        self.assertEqual(sheet_model.model, 'Test Spreadsheet')
        self.assertEqual(sheet_model.res_id, 14)
        self.assertEqual(sheet_model.type, 'Test type')
        self.assertEqual(sheet_model.client_id, 'Test Client')
        self.assertEqual(sheet_model.server_revision_id, 'Test server revision')
        self.assertEqual(sheet_model.next_revision_id, 'Test next revision')
        self.assertEqual(sheet_model.commands, 'Test commands')

    def test_spreadsheet(self):
        """Test various functionalities of the 'spreadsheet.spreadsheet'
         model."""
        owner = self.env['res.users'].create({
            'name': 'Jhon',
            'login': 'testowner',
        })
        spreadsheet = self.env['spreadsheet.spreadsheet'].create({
            'name': 'Test spreadsheet',
            'excel_file_name': 'Test File',
            'filename': '',
            'owner_id': owner.id
        })
        spreadsheet._compute_filename()
        self.assertEqual(spreadsheet.filename, 'Test spreadsheet.json')
        spreadsheet._compute_spreadsheet_raw()
        self.assertEqual(spreadsheet.spreadsheet_raw, {})
        spreadsheet._get_spreadsheet_data()
        self.assertEqual(spreadsheet.spreadsheet_raw, {})
        vals_list = {
            'name': 'Test spreadsheet',
            'excel_file_name': 'Test File',
            'filename': '',
            'owner_id': owner.id
        }
        result = spreadsheet.create(vals_list)
        self.assertTrue(result)

    def test_fields_spreadsheet_import(self):
        """Test fields of the 'spreadsheet.spreadsheet.import.mode' model."""
        self.grp_internal_xml_id = 'base.group_user'
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        grp_test = self.env["res.groups"].create(
            {"name": "test",
             "implied_ids": [Command.set([self.grp_internal.id])]})
        spreadsheet_import = self.env[
            'spreadsheet.spreadsheet.import.mode'].create({
                'name': 'Test Import',
                'code': 'Code',
                'group_ids': [grp_test.id]
            })
        self.assertEqual(spreadsheet_import.name, 'Test Import')
        self.assertEqual(spreadsheet_import.code, 'Code')
        self.assertEqual(spreadsheet_import.group_ids, grp_test)

    def test_spreadsheet_import(self):
        """Test the import functionalities of 'spreadsheet.spreadsheet.
        import'."""
        self.grp_internal_xml_id = 'base.group_user'
        self.grp_internal = self.env.ref(self.grp_internal_xml_id)
        grp_test = self.env["res.groups"].create(
            {"name": "test",
             "implied_ids": [Command.set([self.grp_internal.id])]})
        spreadsheet_import_mode = self.env[
            'spreadsheet.spreadsheet.import.mode'].create({
                'name': 'Test Import',
                'code': 'Code',
                'group_ids': [grp_test.id]
            })
        owner = self.env['res.users'].create({
            'name': 'Jhon',
            'login': 'testowner',
        })
        spreadsheet = self.env['spreadsheet.spreadsheet'].create({
            'name': 'Test spreadsheet',
            'excel_file_name': 'Test File',
            'filename': '',
            'owner_id': owner.id
        })
        spreadsheet_import = self.env['spreadsheet.spreadsheet.import'].create({
            'name': 'Test Spreadsheet',
            'mode_id': spreadsheet_import_mode.id,
            'mode': spreadsheet_import_mode.code,
            'spreadsheet_id': spreadsheet.id
        })
        spreadsheet_import._create_spreadsheet_vals()
        self.assertEqual(spreadsheet_import.name, 'Test Spreadsheet')
        result = spreadsheet_import._insert_spreadsheet_new()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'action_load_spreadsheet')
        result = spreadsheet_import._insert_spreadsheet_add()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'action_load_spreadsheet')
        result = spreadsheet_import._insert_spreadsheet_add_sheet()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'action_load_spreadsheet')

    _LOGGER.info("CY Spreadsheet Test passed")
