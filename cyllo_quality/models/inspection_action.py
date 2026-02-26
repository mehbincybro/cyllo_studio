# -*- coding: utf-8 -*-
from odoo import fields, models


class InspectionAction(models.Model):
    _name = 'inspection.action'
    _description = 'Inspection Actions'

    name = fields.Char(string='Actions')

