# -*- coding: utf-8 -*-
from odoo import models


class ResCompany(models.Model):
    """This model inherits from the 'res.company' model to provide additional
     features and modifications specific to the application's requirements."""
    _inherit = 'res.company'

    def action_open_mapped_accounts(self):
        """This action opens a window displaying the mapped accounts for this company."""
        return {
            'type': 'ir.actions.act_window',
            'name': f"Account Mapping: {self.name}",
            'view_mode': 'tree',
            'res_model': 'account.account',
            'target': 'current',
            'domain': [('company_id', '=', self.id)],
        }
