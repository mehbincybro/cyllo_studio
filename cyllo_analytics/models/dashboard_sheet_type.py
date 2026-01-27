# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardSheetType(models.Model):
    """Dashboard Sheet Type Model"""
    _name = 'dashboard.sheet.type'
    _description = 'Dashboard Sheet Types'

    name = fields.Char('Name')
    image = fields.Image()

