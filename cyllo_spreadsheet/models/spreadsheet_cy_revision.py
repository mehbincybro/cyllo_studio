# -*- coding: utf-8 -*-
from odoo import fields, models


class SpreadsheetCyRevision(models.Model):
    """ Model which is used to track the changes on the spreadsheet.
            used to store the additional content and passed to the spreadsheet
            model"""
    _name = "spreadsheet.cy.revision"
    _description = "Spreadsheet Cyllo Revision"

    model = fields.Char(help="Current model name", required=True)
    res_id = fields.Integer(string="Res Id", help="Storing id of parent model", required=True, index=True)
    type = fields.Char(help="Type of revision for each record")
    client_id = fields.Char(string="Current id", help="Client id")
    server_revision_id = fields.Char(string="Server revision id", help="Revision id")
    next_revision_id = fields.Char(help="Next revision id")
    commands = fields.Char(help="Storing spreadsheet data and row details")
