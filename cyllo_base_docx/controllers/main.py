# -*- coding: utf-8 -*-
import io
from docx import Document
from odoo import http
from odoo.http import request
from odoo.tools import json


class DocReport(http.Controller):
    """
    Controller for handling Docx reports.
    """
    @http.route('/docx_reports', type='http', auth="public")
    def get_docx_report(self, model, options, output_format, report_name):
        """ Generate and return a Docx report in response to an HTTP request. """
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        if output_format == 'docx':
            stream = io.BytesIO()
            document = Document()
            report_obj.get_docx_report(document, json.loads(options))
            document_file_name = report_name
            document.save(stream)
            stream.seek(0)
            return request.make_response(
                stream,
                [('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                 ('Content-Disposition', f'attachment; filename={document_file_name}')])
