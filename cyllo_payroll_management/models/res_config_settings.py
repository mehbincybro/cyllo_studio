# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extends the `res.config.settings` model to add the fields"""
    _inherit = 'res.config.settings'

    batch_move_line = fields.Boolean(string="Batch Account Move Lines",
                                     help="To combine all of the accounting entries for a given time into a single "
                                          "account move line, enable this option. In addition to disabling single "
                                          "payment generations, this will anonymize the accounting entries.",
                                     config_parameter='cyllo_payroll_management.batch_move_line')

    @api.onchange('batch_move_line')
    def _onchange_batch_move_line(self):
        """To set true the batch move line"""
        if self.batch_move_line:
            self.env.user.company_id.batch_move_line = True
        else:
            self.env.user.company_id.batch_move_line = False
