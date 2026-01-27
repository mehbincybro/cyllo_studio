# -*- coding: utf-8 -*-
import base64
import json
from odoo import api, fields, models
from odoo.http import request


class SpreadsheetSpreadsheet(models.Model):
    """ Used to manage spreadsheet record.Adding functionality for managing
        *spreadsheet in the context of document module"""
    _inherit = "spreadsheet.spreadsheet"

    document_file_id = fields.Many2one('document.file', help="For getting record from document", ondelete='cascade')
    is_document = fields.Boolean(help="Identifying document element")

    @api.model_create_multi
    def create(self, vals_list):
        """ Created document while creating spreadsheet from the
                    spreadsheet module directly"""
        spreadsheet = super(SpreadsheetSpreadsheet, self).create(vals_list)
        workspace_id = self.env.ref("cyllo_document_spreadsheet.document_workspace_spreadsheet")
        if not spreadsheet.document_file_id:
            # Creating attachment for the document
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': spreadsheet.name,
                'res_model': 'document.file',
                'res_id': spreadsheet.id,
                'type': 'binary',
                'public': True,
            })
            # Creating document record for the spreadsheet
            document_id = self.env['document.file'].sudo().create({
                'name': spreadsheet.name,
                'extension': 'xlsx',
                'date': fields.Datetime.now(),
                'workspace_id': workspace_id.id,
                'attachment_id': attachment_id.id,
                'is_excel': True,
                'content_url': f"""{
                request.httprequest.host_url[:-1]}/web/content/{
                attachment_id.id}/{spreadsheet.name}"""
            })
            if spreadsheet.data:
                # Updating the file content and file id
                document_id.sudo().update({
                    'attachment': spreadsheet.spreadsheet_data,
                })
            spreadsheet.sudo().update({
                'document_file_id': document_id
            })
        return spreadsheet

    @api.model
    def add_attachment(self, spreadsheet_id):
        """ Generating excel binary file to for attaching it to the ir_attachment
            :param spreadsheet_id: Id of the spreadsheet record to be added on attachment
            :return :Client action for attaching the spreadsheet
        """
        sheet_id = self.sudo().browse(spreadsheet_id)
        if sheet_id.data:
            data_file = json.loads(base64.decodebytes(sheet_id.data).decode("UTF-8"))
            # Return client action to the js function
            return {
                'type': "ir.actions.client",
                'tag': "action_share_spreadsheet",
                'params': {
                    'name': sheet_id.name,
                    'data': data_file,
                    'id': sheet_id.id
                },
            }
