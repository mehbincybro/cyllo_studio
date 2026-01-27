# -*- coding: utf-8 -*-
from odoo import fields, models


class View(models.Model):
    """
    This class inherits from 'ir.ui.view' and includes fields for the Gantt view
    """
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('gantt', 'Gantt')])
