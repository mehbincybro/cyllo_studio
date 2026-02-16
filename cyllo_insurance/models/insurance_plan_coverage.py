from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsurancePlanCoverage(models.Model):
    _name = 'insurance.plan.coverage'
    _description = 'Insurance Plan Coverage'

    plan_id = fields.Many2one('insurance.plan', required=True, ondelete='cascade')
    coverage_id = fields.Many2one('insurance.coverage', required=True)
    coverage_amount = fields.Monetary(required=True)
    deductible = fields.Monetary(default=0)
    coverage_type = fields.Selection(selection=[('covered', 'Covered'), ('not_covered', 'Not Covered')],
                                     default='covered', required=True)
    currency_id = fields.Many2one(related='plan_id.currency_id', store=True)

