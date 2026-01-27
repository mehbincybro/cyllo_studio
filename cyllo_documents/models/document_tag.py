# -*- coding: utf-8 -*-
from odoo import fields, models


class DocumentTag(models.Model):
    """Model for managing document tags."""
    _name = "document.tag"
    _description = 'Document Tag'

    name = fields.Char()

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists!"),]
