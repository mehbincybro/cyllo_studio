# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    """To create journal items"""
    _inherit = 'account.move'

    journal_item_ids = fields.One2many('account.journal.item', 'account_move_id', copy=True)


class AccountJournalItem(models.Model):
    """To create the journal items"""
    _name = 'account.journal.item'
    _description = 'Account Journal Item'

    account_id = fields.Many2one('account.account', help='To add the accounts for the entries')
    partner_id = fields.Many2one('res.partner', help='To add the partner')
    label = fields.Char(help='To get the label of the entry')
    debit = fields.Monetary(help='To get the debit amount')
    credit = fields.Monetary(help='To get the credit amount')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(comodel_name='res.currency', default=lambda self: self.env.company.currency_id.id)
    account_move_id = fields.Many2one('account.move', help='To get the relation of the account move')


class AccountMoveLine(models.Model):
    """To add a field for passing batch_id"""
    _inherit = 'account.move.line'

    batch_id = fields.Integer(help='To get batch id from the batch payslip')
