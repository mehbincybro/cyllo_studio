# -*- coding: utf-8 -*-
from odoo import fields, models


class SupportServiceCategory(models.Model):
    """ Class for Support Service Category model """
    _name = "support.service.category"
    _description = "Support Service Category"

    name = fields.Char(string="Category", required=True, help="Ticket category")
    parent_id = fields.Many2one('support.service.category', help="Parent of the category")
    description = fields.Html(help="Category description")
