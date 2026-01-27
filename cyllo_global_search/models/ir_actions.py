# -*- coding: utf-8 -*-
from odoo import fields, models


class IrActionsActWindow(models.Model):
    """Extends the 'ir.actions.act_window' model to add a custom field."""
    _inherit = 'ir.actions.act_window'

    custom_wizard_class = fields.Char(string="Custom class cor wizard")


class IrActions(models.Model):
    """Extends the 'ir.actions.actions' model."""
    _inherit = 'ir.actions.actions'

    def _get_readable_fields(self):
        """ return the list of fields that are safe to read
        Fetched via /web/action/load or _for_xml_id method
        Only fields used by the web client should included
        Accessing content useful for the server-side must
        be done manually with superuser"""
        return {
            "binding_model_id", "binding_type", "binding_view_types",
            "display_name", "help", "id", "name", "type", "xml_id",
            "custom_wizard_class",
        }
