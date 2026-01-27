# -*- coding: utf-8 -*-
from odoo import fields, models


class FieldSelection(models.TransientModel):
    """ Creates field selection """
    _name = "field.selection"
    _description = 'Field Selection'

    value = fields.Char(help="Key of newly creating field", required=True)
    name = fields.Char(help="Option that shows in newly creating selection field", required=True)
    create_id = fields.Many2one(comodel_name='field.create', string='Connection Field',
                                help="Connection field to 'field.create' model")
