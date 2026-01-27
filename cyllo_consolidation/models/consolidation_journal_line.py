# -*- coding: utf-8 -*-
from odoo import fields, models


class ConsolidationJournalLine(models.Model):
    """This model represents individual lines within consolidation journals,
    linking consolidated accounts with specific amounts and balances."""
    _name = 'consolidation.journal.line'
    _description = 'Consolidation Journal Line'

    journal_id = fields.Many2one('consolidation.journal',
                                 help='Consolidation journal associated with this journal line')
    account_id = fields.Many2one('consolidation.account', string='Consolidated Account',
                                 help='Consolidated account linked with this journal line')
    group_id = fields.Many2one('consolidation.group',
                               help='Select the group associated with this consolidation account.')
    balance = fields.Monetary(help='Balance for this journal line')
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id',
                                  help='Currency associated with the journal.')
