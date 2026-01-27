# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import content_disposition, Controller, request


class DownloadSpreadsheet(Controller):
    """Download the Spreadsheet file from the server"""

    @http.route('/spreadsheet/xlsx', type='http', auth="user", methods=["POST"])
    def download_spreadsheet(self, zip_name, files):
        """
        Creating Excel file for downloading.
        :param zip_name: Name of the spreadsheet
        :param files: File content of the spreadsheet
        :return: The response that generated after creating the Excel
        """
        file = json.loads(files)
        data = request.env['spreadsheet.spreadsheet'].get_xlsx_file(file)
        headers = [
            ('Content-Type', 'application/vnd.ms-excel'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Disposition', content_disposition(zip_name))
        ]
        response = request.make_response(data, headers)
        return response
