# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """
       Extends the base 'res.config.settings' model to include
       additional configuration settings related to timesheet durations
       and rounding.
   """
    _inherit = 'res.config.settings'

    minimal_duration = fields.Integer(help="Field to set the minimum timesheet duration", default=15,
                                      config_parameter="cyllo_timesheet_grid.minimal_duration")
    round_up = fields.Integer(help="Field to set the rounding time", default=15,
                              config_parameter="cyllo_timesheet_grid.round_up")
