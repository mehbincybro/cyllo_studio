# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardConfig(models.Model):
    """Menu Model"""
    _inherit = "ir.ui.menu"

    is_cyllo_analytic_menu = fields.Boolean(string="Cyllo Analytics Menu")
