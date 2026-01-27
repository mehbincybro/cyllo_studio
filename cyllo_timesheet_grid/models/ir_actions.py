# -*- coding: utf-8 -*-
from odoo import fields, models


class IrActionsActWindowView(models.Model):
    """
       Extends the base 'ir.actions.act_window.view' model to include
       a new view mode called 'grid'.
   """
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('grid', "Grid")], ondelete={'grid': 'cascade'})
