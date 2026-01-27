# -*- coding: utf-8 -*-
from odoo import fields, models


class IrModelFields(models.Model):
    """ Adding a new field to understand the newly created fields."""
    _inherit = 'ir.model.fields'

    is_dynamic_field = fields.Boolean(string="Dynamic Field", help="Is this field is newly added")
