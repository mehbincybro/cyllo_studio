from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsurancePlanCoverage(models.Model):
    _name = 'insurance.plan.coverage'
    _description = 'Insurance Plan Coverage'

    plan_id = fields.Many2one('insurance.plan', required=True, ondelete='cascade')
    coverage_id = fields.Many2one('insurance.coverage', required=True)
    coverage_amount = fields.Monetary(required=True)
    # deductible = fields.Monetary(default=0)
    coverage_type = fields.Selection(selection=[('covered', 'Covered'), ('addons', 'Addons')],
                                     default='covered', required=True)
    currency_id = fields.Many2one(related='plan_id.currency_id', store=True)

    @api.constrains('plan_id', 'coverage_id')
    def _check_duplicate_coverage(self):
        for rec in self:
            if not rec.plan_id or not rec.coverage_id:
                continue

            duplicates = self.search([
                ('plan_id', '=', rec.plan_id.id),
                ('coverage_id', '=', rec.coverage_id.id),
                ('id', '!=', rec.id)
            ])

            if duplicates:
                raise ValidationError(
                    "This coverage is already added to this plan."
                )


