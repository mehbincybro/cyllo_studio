from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetInsurance(models.TransientModel):
    """ Wizard model for asset insurance claiming"""
    _name = 'asset.insurance'
    _description = 'Asset Insurance'

    asset_id = fields.Many2one('asset.asset', string='Asset ID', required=True, readonly=True)
    repair_id = fields.Many2one('maintenance.request', string='Repair ID', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True,
                                  default=lambda self: self.env.company.currency_id)
    total_amount = fields.Monetary(string="Total Repair Cost", readonly=True)
    insurance_amount = fields.Monetary(string="Claiming amount", default=100)
    reimburse_after_invoice = fields.Boolean(default=False)
    invoiced_amount = fields.Monetary()
    expense = fields.Monetary()

    @api.constrains('insurance_amount')
    def _check_assign_date(self):
        """Function for checking the percentage amount"""
        if self.insurance_amount > self.expense or self.insurance_amount < 0:
            raise UserError(
                _('Please enter a valid insurance amount'))
        if self.insurance_amount > self.expense - self.invoiced_amount:
            raise UserError(
                _('The Total invoiced Amount exceeds expense'))

    def action_claim(self):
        return self.repair_id.with_context(
            insurance_amount=self.insurance_amount,
            from_insurance_wizard=True,
            is_reimbursed=self.reimburse_after_invoice,
        ).action_claim_insurance()
