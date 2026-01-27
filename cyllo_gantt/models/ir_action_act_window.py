# -*- coding: utf-8 -*-
from odoo import fields, models


class WindowView(models.Model):
    """
    This class inherits from 'ir.actions.act_window.view' and includes fields
    for the Gantt view mode.
    """
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('gantt', 'Gantt')], ondelete={'gantt': 'cascade'})
