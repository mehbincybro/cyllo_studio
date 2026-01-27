# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardPresentation(models.TransientModel):
    """Dashboard Presentation Model"""
    _name = 'dashboard.presentation'
    _description = 'Dashboard Presentation'

    chart_data = fields.Json()
    type = fields.Char()
    style = fields.Char()
    style_json = fields.Json()
    theme = fields.Char()
    theme_json = fields.Json()
    auto_slide = fields.Boolean()
    auto_slide_time = fields.Integer(string='Auto Slide Duration')
    title_page = fields.Boolean()
    title_page_heading = fields.Char()
    title_page_subheading = fields.Char()
