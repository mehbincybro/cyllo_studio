# -*- coding: utf-8 -*-
import base64
import json
from odoo import api, fields, models, _


class DocumentFile(models.Model):
    """ Used for managing document files"""
    _inherit = "document.file"

    is_excel = fields.Boolean(help="For identifying excel record")

    @api.model
    def open_spreadsheet(self, file):
        """ While clicking Excel file we can open spreadsheet
            :param file: file content to be open
        """
        document_id = self.browse(file.get('id'))
        if file.get('extension') == "xlsx" and not document_id.is_locked:
            spreadsheet_id = self.env['spreadsheet.spreadsheet'].sudo().search(
                [('document_file_id', '=', file.get('id'))])
            # Get the spreadsheet id and return to the js function
            return spreadsheet_id.id

    @api.model
    def action_upload_document(self, *args):
        """ Changing the default workspace for Excel into Spreadsheet
            :param args: Details of the uploaded file
        """
        workspace_id = self.env.ref("cyllo_document_spreadsheet.document_workspace_spreadsheet")
        if '.xlsx' in args[0].get('file_name'):
            # Updated the workspace id
            args[0].update({
                'workspace_id': workspace_id.id
            })
        return super(DocumentFile, self).action_upload_document(*args)

    def click_download(self):
        """ Downloading an Excel file from the spreadsheet"""
        if self.extension == 'xlsx':
            spreadsheet_id = self.env['spreadsheet.spreadsheet'].sudo().search([('document_file_id', '=', self.id)])
            data_file = json.loads(base64.decodebytes(spreadsheet_id.data).decode("UTF-8"))
            # Loading client action for downloading the spreadsheet
            return {
                'type': "ir.actions.client",
                'tag': "action_download_spreadsheet",
                'params': {
                    'name': spreadsheet_id.name,
                    'data': data_file,
                },
            }
        return super(DocumentFile, self).click_download()

    @api.model_create_multi
    def create(self, vals_list):
        """ Creating spreadsheet corresponding to the document
            :param vals_list:List of dictionary contains field values
        """
        document = super(DocumentFile, self).create(vals_list)
        if document.extension == 'xlsx':
            # Creating attachment for corresponding to document
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': document.name,
                'res_model': 'document.file',
                'res_id': document.id,
                'public': True,
            })
            document.write({
                'attachment_id': attachment_id,
                # Writing attachment id and document content
                # share url to document
                'content_url': f"""{self.env['ir.config_parameter'].sudo().
                get_param('web.base.url')}/web/content/{
                attachment_id.id}/{document.name}"""
            })
        if not document.is_excel and document.extension == "xlsx":
            # Creating spreadsheet while creating an Excel document
            self.env['spreadsheet.spreadsheet'].sudo().create({
                'name': document.name,
                'owner_id': self.env.uid,
                'spreadsheet_data': document.attachment,
                'excel_file_name': document.display_name,
                'document_file_id': document.id,
                'is_document': True
            })
        return document

    @api.model
    def download_zip_function(self, document_selected):
        """ For downloading multiple file as a zip
            :param document_selected: Ids of the selected documents
        """
        for document in self.sudo().browse(document_selected):
            if document.extension == "xlsx":
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'message': _(
                            "Multiple file download is not available for excel"
                            " files.Please download individually"),
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
        return super(DocumentFile, self).download_zip_function(
            document_selected)

    def unlink(self):
        """ Passing spreadsheet content to the trash while moving Excel
            file to the trash"""
        if self.extension == "xlsx":
            spreadsheet_id = self.env['spreadsheet.spreadsheet'].search([('document_file_id', '=', self.id)])
            trash_id = self.env['document.trash'].sudo().search([('attachment_id', '=', self.attachment_id.id)])
            # Updating trash with spreadsheet content
            trash_id.update({
                'spreadsheet_data': spreadsheet_id.data
            })
        return super(DocumentFile, self).unlink()
