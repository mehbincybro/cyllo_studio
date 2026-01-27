# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class XLSXReportController(http.Controller):
    """ Odoo Controller for generating XLSX reports."""
    @http.route('/xlsx_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_report_xlsx(self, model, options, output_format, report_name):
        """Generate an XLSX report based on the provided data and return it as a response.
            Args:
                model (str): The name of the model on which the report is based.
                options (str): The data required for generating the report.
                output_format (str): The desired output format for the report (e.g., 'xlsx').
                report_name (str): The name to be given to the generated report file.
            Returns:
                Response: The generated report file as a response.
            Raises:
                Exception: If an error occurs during report generation.
            """
        report_obj = request.env[model].with_user(request.session.uid)
        token = 'dummy-because-api-expects-one'
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_xlsx_report(options, response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': http.serialize_exception(e)
            }
            return request.make_response(html_escape(json.dumps(error)))
