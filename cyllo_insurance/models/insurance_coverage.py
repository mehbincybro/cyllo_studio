from odoo import models, fields


class InsuranceCoverage(models.Model):
    _name = 'insurance.coverage'
    _description = 'Insurance Coverage'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)
