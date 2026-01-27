from odoo.exceptions import UserError
from odoo import models,_

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_uninstall(self):
        for module in self:
            if module.name == 'cyllo_accounting_pdc':
                if self.env['account.pdc.payment'].sudo().search_count([]):
                    raise UserError(
                        _("You cannot uninstall Accounting PDC because PDC payments exist.")
                    )
        return super().button_immediate_uninstall()

