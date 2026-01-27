# -*- coding: utf-8 -*-
import random
from odoo import fields, models


class AllocationType(models.Model):
    """Represents planning allocation type."""
    _name = 'allocation.type'
    _description = "Planning Allocation Type"

    name = fields.Char(required=True)
    color = fields.Char(help="Choose color for allocation", default=lambda self: self._default_color())
    description = fields.Text(help="Allocation type description")
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, string="Created By")
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def _default_color(self):
        """Function to get random color for allocation type"""
        return '#{:06x}'.format(random.randint(0, 0xFFFFFF))
