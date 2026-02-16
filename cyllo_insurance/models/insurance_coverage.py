from odoo import models, fields


class InsuranceCoverage(models.Model):
    _name = 'insurance.coverage'
    _description = 'Insurance Coverage'

    name = fields.Char(required=True,help="Name of the coverage.")
    code = fields.Char(help="Short code to identify the coverage.")
    description = fields.Text(help="Description of what this coverage includes.")
    active = fields.Boolean(default=True,help="Uncheck to hide this coverage without deleting it.")
