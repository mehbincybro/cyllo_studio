# -*- coding: utf-8 -*-
from odoo import fields, models


class SupportServiceStage(models.Model):
    """ Class defines Support Service Stage model """
    _name = "support.service.stage"
    _description = "Support Service Stage"
    _order = "sequence"

    name = fields.Char(string="Stage", required=True, help="Add more stages")
    sequence = fields.Integer(default=1, help="Order of stage")
    is_closed = fields.Boolean(string="Is Closed Stage", help="Enable if it is closed stage")
    is_fold = fields.Boolean(string="Fold", help="Stage folded in kanban")
