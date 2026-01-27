# -*- coding: utf-8 -*-
from odoo import fields, models


class IrUiView(models.Model):
    """
    In the class IrUiView is adding fields to the 'ir.ui.view'
    """
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('map_view', 'Map')], help='View type.')
