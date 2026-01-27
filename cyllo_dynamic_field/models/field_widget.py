# -*- coding: utf-8 -*-
from odoo import fields, models


class FieldWidget(models.Model):
    """ Creates Field Widget """
    _name = 'field.widget'
    _description = 'Field Widget'

    name = fields.Char(help="name to add in the xml for apply the widget", required=True)
    datatype = fields.Char(string='Value', required=True, help="Value to show the name of widget")
