# -*- coding: utf-8 -*-
from odoo import fields, models


class CreateExcel(models.TransientModel):
    """ Wizard that used to create spreadsheet from kanban view"""
    _name = "create.excel"
    _description = "Wizard for Creating Excel Sheet"

    name = fields.Char(help="Name of the spreadsheet")

    def action_create_spreadsheet(self):
        """Creating spreadsheet from the wizard"""
        workspace_id = self.env.ref("cyllo_document_spreadsheet.document_workspace_spreadsheet")
        # Creating document for spreadsheet document
        document_id = self.env['document.file'].sudo().create({
            'name': self.name,
            'date': fields.Datetime.now(),
            'extension': 'xlsx',
            'workspace_id': workspace_id.id,
            'is_excel': True
        })
        # Creating spreadsheet record
        spreadsheet_id = self.env['spreadsheet.spreadsheet'].sudo().create({
            "name": self.name,
            'document_file_id': document_id.id,
            'owner_id': self.env.uid,
            'is_document': True,
        })
        # Returns client action for displaying created spreadsheet
        return {
            'type': "ir.actions.client",
            'tag': "action_load_spreadsheet",
            'params': {
                'spreadsheet_id': spreadsheet_id.id,
                'model': 'spreadsheet.spreadsheet',
            },
        }
