from odoo import models, fields


class InsurancePolicyType(models.Model):
    _name = 'insurance.policy.type'
    _description = 'Insurance Policy Type'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
