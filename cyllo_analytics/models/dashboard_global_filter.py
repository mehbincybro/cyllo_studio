# -*- coding: utf-8 -*-

from odoo import fields, models


class DashboardGlobalFilter(models.Model):
    """This module defines the DashboardGlobalFilter model."""
    _name = 'dashboard.global.filter'
    _description = 'Dashboard Global Filter'

    name = fields.Char()
    dashboard_config_id = fields.Many2one('dashboard.config')
