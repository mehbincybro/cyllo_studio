# -*- coding: utf-8 -*-
from odoo import api, models


class AccountAnalyticLine(models.Model):
    """
        Extends the base 'account.analytic.line' model to include a custom
        method 'write_task'.
    """
    _inherit = "account.analytic.line"

    @api.model
    def write_task(self, vals):
        """
            Update the 'task_id' field of the associated 'analytic_account_id'
            record with the provided value.
            :param vals: A dictionary containing values to update.
            :return: True if the operation is successful.
        """
        analytic_account_id = self.browse(vals.get('analytic_account_id'))
        analytic_account_id.update({
            'task_id': vals.get('task_id')
        })
        return True
