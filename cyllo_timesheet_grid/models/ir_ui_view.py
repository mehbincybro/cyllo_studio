# -*- coding: utf-8 -*-
from odoo import fields, models


class View(models.Model):
    """
        Extends the base 'ir.ui.view' model to include a new type of view
        called 'grid'.
    """
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('grid', "Grid")])
