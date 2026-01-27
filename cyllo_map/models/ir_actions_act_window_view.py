# -*- coding: utf-8 -*-
from odoo import fields, models


class ActWindowView(models.Model):
    """
    In the class ActWindowView is adding fields to the
    'ir.actions.act_window.view'
    """
    _inherit = 'ir.actions.act_window.view'

    view_mode = fields.Selection(selection_add=[('map_view', 'Map')],
                                 ondelete={'map_view': 'cascade'}, help="Select the view mode")
