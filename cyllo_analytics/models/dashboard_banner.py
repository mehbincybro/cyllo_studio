# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardBanner(models.Model):
    """Model representing a dashboard banner."""
    _name = "dashboard.banner"
    _description = "Dashboard Banner"
    _inherit = ['image.mixin']

    name = fields.Char(required=True)

