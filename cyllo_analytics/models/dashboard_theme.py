# -*- coding: utf-8 -*-
from odoo import fields, models


class DashboardTheme(models.Model):
    """Dashboard Theme Model"""
    _name = 'dashboard.theme'
    _description = 'Dashboard Theme'

    name = fields.Char(required=True)
    background = fields.Char()
    title = fields.Char()
    subtitle = fields.Char()
    theme_color_ids = fields.One2many('dashboard.theme.color', 'theme_id', string='Theme')
    label_text = fields.Char()
    border_width = fields.Integer()
    border_color = fields.Char()

    def read_theme(self):
        """Read the theme data from the database and return it as a dictionary"""
        data = self.read(["name", "background", "title", "subtitle", "theme_color_ids", "label_text", "border_width",
                          "border_color"])
        if data:
            new_vals = data[0].copy()
            new_vals["theme_color_ids"] = []
            for val in data[0]['theme_color_ids']:
                new_vals["theme_color_ids"].append(self.env["dashboard.theme.color"].browse(val).name)
            return new_vals
        return {}


class DashboardThemeColor(models.Model):
    """Dashboard Theme Color Model"""
    _name = 'dashboard.theme.color'
    _description = 'Dashboard Theme Color'

    name = fields.Char(string='Color', required=True)
    theme_id = fields.Many2one('dashboard.theme')
