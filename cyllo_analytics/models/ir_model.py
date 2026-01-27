# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IrModel(models.Model):
    """Model representing various models in the system."""
    _inherit = "ir.model"

    table_name = fields.Char('Table Name', help="Name of the field is auto completed using post_init_hook "
                                                "to get the field name for reference")

    @api.model
    def get_model_from_table(self, table):
        """Retrieve the model associated with a given table name."""
        model = self.search([('table_name', '=', table)])
        if model:
            return self.env["dashboard.sheet"].get_data(model.id)
        return {}
