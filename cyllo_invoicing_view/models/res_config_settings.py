# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Inheriting this module to install cyllo_budget_management module
    when the budget management in settings is checked """
    _inherit = 'res.config.settings'

    module_cyllo_budget_management = fields.Boolean(string="Budget Management")
