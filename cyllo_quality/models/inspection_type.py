# -*- coding: utf-8 -*-
from odoo import fields, models


class InspectionType(models.Model):
    _name = 'inspection.type'
    _description = 'Inspection Types'

    name = fields.Char(string='Type')