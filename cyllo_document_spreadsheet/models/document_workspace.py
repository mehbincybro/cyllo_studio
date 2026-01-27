# -*- coding: utf-8 -*-
from odoo import models


class DocumentWorkspace(models.Model):
    """ Used for managing workspace and make its name unique used
            to prevent duplicate workspace issue"""
    _inherit = 'document.workspace'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "This name already exists!"),
    ]
