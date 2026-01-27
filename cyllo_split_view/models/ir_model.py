# -*- coding: utf-8 -*-
from odoo import api, fields, models


class IrModel(models.Model):
    """
       Extend the 'ir.model' model to add a boolean field for split views.
       """
    _inherit = "ir.model"

    list_split_view = fields.Boolean(help="Field to split views")

    @api.model
    def add_split_view(self, rec):
        """
        Update the 'list_split_view' field to True for the given model.
        :param rec: The model to update.
        """
        self.env['ir.model'].search([('model', '=', rec)]).write({
            'list_split_view': True
        })

    @api.model
    def remove_split_view(self, rec):
        """
        Update the 'list_split_view' field to False for the given model.
        :param rec: The model to update.
        """
        self.env['ir.model'].search([('model', '=', rec)]).write({
            'list_split_view': False
        })
