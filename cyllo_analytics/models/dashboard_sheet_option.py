# -*- coding: utf-8 -*-

from odoo import fields, models


class DashboardSheetOption(models.Model):
    """Model representing options for dashboard sheets."""
    _name = "dashboard.sheet.option"
    _description = "Dashboard Sheet Option"

    dashboard_sheet_id = fields.Many2one("dashboard.sheet")
    attributes = fields.Json("Attributes")
    dashboard_config_id = fields.Many2one("dashboard.config")
