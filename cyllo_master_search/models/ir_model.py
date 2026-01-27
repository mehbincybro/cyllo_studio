# -*- coding: utf-8 -*-
from odoo import fields, models


class IrModel(models.Model):
    """This class extends the 'ir.model' model in Odoo to add a new boolean field,
     'master_search'."""
    _inherit = "ir.model"

    master_search = fields.Boolean(help="Enable this to include the model in the master search.")
