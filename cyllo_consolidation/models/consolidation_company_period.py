# -*- coding: utf-8 -*-
from odoo import fields, models


class ConsolidationCompanyPeriod(models.Model):
    """This model represents periods for consolidation within a company."""
    _name = 'consolidation.company.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Company Period'

    company_id = fields.Many2one('res.company', readonly=True,
                                 help='The company associated with this consolidation period.')
    currency_id = fields.Many2one(related='company_id.currency_id',
                                  help='The currency used by the company for consolidation.')
    period_id = fields.Many2one('consolidation.period', string="Periods",
                                help='The specific period associated with this consolidation entry.')
    consolidation_rate = fields.Float(string='Consolidation rate (%)', default='100',
                                      help='The percentage rate of consolidation for this period.')
    start_date = fields.Date(readonly=True, help='Start date of the consolidation period')
    end_date = fields.Date(readonly=True, help='End date of the consolidation period')
