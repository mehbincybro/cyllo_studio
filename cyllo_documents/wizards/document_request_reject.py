# -*- coding: utf-8 -*-
from odoo import fields, models


class DocumentRequestReject(models.TransientModel):
    """model help to reject document request"""
    _name = 'document.request.reject'
    _description = 'Document Request Reject Wizard'

    reject_reason = fields.Text(help="store reject reason", required=True)
    document_request_id = fields.Many2one('request.document')

    def action_reject_request(self):
        """Method used to reject a document request"""
        self.document_request_id.state = 'rejected'
        self.document_request_id.reject_reason = self.reject_reason
