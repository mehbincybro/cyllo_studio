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
        spreadsheet_id = self.env['spreadsheet.sheet'].sudo().create({
            "name": self.name,
            'document_file_id': document_id.id,
            # 'owner_id': self.env.uid,
            # 'is_document': True,
        })
        return {
            'type': "ir.actions.client",
            'tag': "main_spreadsheet",
            'context': {
                'resId': spreadsheet_id.id,
            },
        }
