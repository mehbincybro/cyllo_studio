# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Extends the `res.config.settings` model to add the fields"""
    _inherit = 'res.company'

    batch_move_line = fields.Boolean(string='Batch Move', help='To get the value from the settings')
