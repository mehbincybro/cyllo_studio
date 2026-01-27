# -*- coding: utf-8 -*-
from odoo import fields, models


class SpreadsheetSpreadsheetImportMode(models.Model):
    """ Determine the spreadsheet import mode."""
    _name = "spreadsheet.spreadsheet.import.mode"
    _description = "Import Mode"
    _order = "sequence asc"

    sequence = fields.Integer(default=20)
    name = fields.Char(required=True, translate=True, help="Name of the import mode")
    code = fields.Char(help="For identifying the import mode", required=True)
    group_ids = fields.Many2many("res.groups", string="Groups", help="Adding access rights")
