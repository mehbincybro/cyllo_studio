# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class WebsiteDocumentsUpload(http.Controller):
    """Controller for handling document uploads and requests on the website."""

    @http.route('/website/documents', type="json", csrf=False)
    def website_docs(self, thumbnail, file, file_name, workspace_id):
        """
        function : website form submit controller,
        it creates a record in 'document.file'
        :param thumbnail, file, file_name, workspace_id
        """
        val_list = {
            'file': file,
            'file_name': file_name,
            'workspace_id': workspace_id,
            'preview_image': thumbnail
        }
        file_id = request.env['document.file']
        file_id.action_upload_document(val_list)

    @http.route('/website/documents_request', type="http", auth="user", website=True, csrf=False)
    def website_docs_request(self, **post):
        """ :function : website form submit controller for requested documents, it creates a record in document.file
        :param post: form-data
        :return: redirect to /my/document_request"""
        request_id = request.env['request.document'].browse(int(post['rec_id']))
        val_list = {'file': base64.b64encode(post['file'].read()),
                    'file_name': post['file'].filename, 'workspace_id': int(post['workspace'])}
        file_id = request.env['document.file']
        file_id.action_upload_document(val_list)
        request_id.state = 'accepted'
        return request.redirect("/my/document_request")

    @http.route('/website/documents_request_reject', type="http", auth="user", website=True, csrf=False)
    def document_request_reject(self, **post):
        """
        :function accept document reject and update document.request
        :param post: form-data
        :return: redirect to /my/document_request
        """
        request_id = request.env['request.document'].browse(int(post['req_id']))
        request_id.state = 'rejected'
        request_id.reject_reason = post['reason']
        return request.redirect("/my/document_request")
