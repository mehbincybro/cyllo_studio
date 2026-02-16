from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsurancePlanCoverage(models.Model):
    _name = 'insurance.policy.coverage'
    _description = 'Insurance Policy Coverage'

    policy_id = fields.Many2one('insurance.policy', required=True, ondelete='cascade')
    coverage_id = fields.Many2one('insurance.coverage', required=True)
    coverage_amount = fields.Monetary(required=True)
    # deductible = fields.Monetary(default=0)
    coverage_type = fields.Selection(selection=[('covered', 'Covered'), ('addons', 'Addons')],
                                     default='covered', required=True)
    currency_id = fields.Many2one(related='policy_id.currency_id', store=True)
    addon_added = fields.Boolean(default=False)

    @api.constrains('policy_id', 'coverage_id')
    def _check_duplicate_coverage(self):
        for rec in self:
            if not rec.policy_id or not rec.coverage_id:
                continue

            duplicates = self.search([
                ('policy_id', '=', rec.policy_id.id),
                ('coverage_id', '=', rec.coverage_id.id),
                ('id', '!=', rec.id)
            ])

            if duplicates:
                raise ValidationError(
                    "This coverage is already added to this policy."
                )

    def action_add_addons(self):
            for rec in self:
                if rec.coverage_type != 'addons':
                    raise ValidationError("Only Addons can be added to premium.")

                if rec.addon_added:
                    raise ValidationError("Addon already added to premium.")

                rec.addon_added = True

