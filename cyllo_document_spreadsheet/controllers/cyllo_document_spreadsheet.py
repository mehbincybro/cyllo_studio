# -*- coding: utf-8 -*-
import base64
import json
from odoo import http
from odoo.http import request, content_disposition, Controller


class AttachSpreadsheet(Controller):
    """
        This controller handles spreadsheet related actions
    """
    @http.route('/spreadsheet/create/xlsx', type='json', auth="user", methods=["POST"])
    def attach_spreadsheet(self, name, files, id):
        """
        Creating and attaching excel binary file to ir_attachment which will
                    coming as a json file loaded along with a client action
        :param name: Name of the spreadsheet
        :param files: File content of the spreadsheet
        :param id: Id of the corresponding spreadsheet record
        :return: The response that generated after creating the Excel
        """
        spreadsheet_id = request.env['spreadsheet.spreadsheet'].browse(id)
        files = json.loads(files)
        data = request.env['spreadsheet.spreadsheet'].get_xlsx_file(files)
        if spreadsheet_id.document_file_id.attachment_id:
            spreadsheet_id.document_file_id.attachment_id.sudo().write({
                'datas': base64.b64encode(data)
            })
        headers = [
            ('Content-Type', 'application/vnd.ms-excel'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Disposition', content_disposition(name))
        ]
        response = request.make_response(data, headers)
        return response
