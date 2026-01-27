# -*- coding: utf-8 -*-
from odoo import fields, models


class Blog(models.Model):
    """Inherit blog.blog model to add the websites field to make the blogs appear in multiple websites"""
    _inherit = 'blog.blog'

    website_ids = fields.Many2many(comodel_name='website', string='Websites',
                                   help="Websites on which the blog have to appear")
