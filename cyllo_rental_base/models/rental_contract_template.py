# -*- coding: utf-8 -*-
from odoo import fields, models


class RentalContractTemplate(models.Model):
    """Template for the rental contract"""
    _name = "rental.contract.template"
    _description = "Template for the rental contract"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(help="Name of the template", check_company=True, required=True)
    contract_line_ids = fields.One2many(comodel_name='contract.lines', inverse_name='contract_template_id',
                                        help='The products associated with this rental contract')
    company_id = fields.Many2one(comodel_name='res.company', required=True, index=True,
                                 default=lambda self: self.env.company,
                                 help='The company associated with this rental contract')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  help='The currency used for transactions related to this rental contract')
    price = fields.Monetary(string="Contract Price", help="Charge of the contract")

    _sql_constraints = [('rental_contract_template_name_unique', 'unique(name)',
                         'There is already a template with this name')]
