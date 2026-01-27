# -*- coding: utf-8 -*-
from odoo import fields, models


class HrIncidentCategory(models.Model):
    """Model for managing incident categories.
        This model defines categories for incidents, including a name,
        description and the company the category belongs to.
        """
    _name = 'hr.incident.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Incident Category"

    name = fields.Char(required=True)
    description = fields.Html(help='Describe the category')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
