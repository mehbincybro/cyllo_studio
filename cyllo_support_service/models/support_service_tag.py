# -*- coding: utf-8 -*-
from odoo import fields, models


class SupportServiceTag(models.Model):
    """ Class to define support service Tag model """
    _name = "support.service.tag"
    _description = "Support Service Tag"

    name = fields.Char(string="Tag", required=True, help="Indicating from which the ticket generated")
    color = fields.Integer(help="Tag color")
