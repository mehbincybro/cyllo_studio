from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetInsurance(models.TransientModel):
    """ Wizard model for asset insurance claiming"""
    _name = 'asset.insurance'
    _description = 'Asset Insurance'

    asset_id = fields.Many2one('asset.asset', string='Asset ID', required=True, readonly=True)
    repair_id=fields.Many2one('maintenance.request', string='Repair ID', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    total_amount = fields.Monetary(string="Total Repair Cost", readonly=True)
    insurance_percentage = fields.Float(string="Insurance Deduction in %", default=100)
    reimburse_after_invoice = fields.Boolean(default=False)

    def action_create_bill(self):
        print("CREATE INV",self.repair_id.id)
        return self.repair_id.with_context(
            insurance_percentage=self.insurance_percentage,
            from_insurance_wizard=True,
            is_reimbursed=self.reimburse_after_invoice,
        ).action_create_bill()


