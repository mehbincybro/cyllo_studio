from odoo import models, fields


class InsurancePolicyType(models.Model):
    _name = 'insurance.policy.type'
    _description = 'Insurance Policy Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, help="Name of the policy type.")
    code = fields.Char(required=True, help="Short code for the policy type.")
    description = fields.Text(help="Description of this policy type.")
    sequence = fields.Integer(default=10, help="Order of display.")
    active = fields.Boolean(default=True, help="Uncheck to archive this policy type.")
