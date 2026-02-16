from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsurancePlanCoverage(models.Model):
    _name = 'insurance.policy.coverage'
    _description = 'Insurance Policy Coverage'

    policy_id = fields.Many2one('insurance.policy', required=True, ondelete='cascade')
    coverage_id = fields.Many2one('insurance.coverage', required=True)
    coverage_amount = fields.Monetary(required=True)
    deductible = fields.Monetary(default=0)
    coverage_type = fields.Selection(selection=[('covered', 'Covered'), ('addons', 'Addons')],
                                     default='covered', required=True)
    currency_id = fields.Many2one(related='policy_id.currency_id', store=True)
