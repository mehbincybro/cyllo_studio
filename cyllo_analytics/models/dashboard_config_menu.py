# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardConfigMenu(models.TransientModel):
    """Dashboard Configuration Menu Model"""
    _name = 'dashboard.config.menu'
    _description = "Dashboard Configuration Menu"

    name = fields.Char(help='Add the name for the new menu')
    menu_id = fields.Many2one('ir.ui.menu', string='Parent Menu', help='Choose the parent menu')
