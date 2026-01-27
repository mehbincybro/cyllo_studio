# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class DocumentRequestAccept(models.TransientModel):
    """model help to Accept and upload document request"""
    _name = 'document.request.accept'
    _description = 'Document Request Accept Wizard'

    document_file = fields.Binary(string='File', help="Choose file")
    workspace_id = fields.Many2one('document.workspace', readonly=True)
    description = fields.Char(help='Add description')
    document_request_id = fields.Many2one('request.document')
    filename = fields.Char(string='File Name')

    def action_accept_request(self):
        """Method used to Accept the document request and upload a file"""
        self.document_request_id.state = 'accepted'
        self.env['document.file'].action_upload_document({'file': self.document_file,
                                                          'file_name': self.filename,
                                                          'workspace_id': self.workspace_id.id})

