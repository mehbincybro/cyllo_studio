# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BudgetLinesConfiguration(models.Model):
    """ Model used to store budget lines, perform budget related functions """
    _name = 'budget.lines.configuration'
    _description = 'Budget Management Lines configuration '

    budget_line_id = fields.Many2one('budget.lines', help='Refers to the budget line ')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Child Account', help='Category')
    type = fields.Selection(selection=[('amount', 'Amount'), ('percentage', 'Percentage')],
                            help='Choose the type to distribute amount')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id.id)
    amount = fields.Monetary(help='Distribute the amount from the budget line', currency_field='currency_id')
    percentage = fields.Float(help='Distribute the budget line amount According to given percentage')
    practical_amount = fields.Monetary(help='The Practical Amount',currency_field='currency_id')
    achievement = fields.Float(help='Distribute the budget line amount According to given Amount')

    @api.onchange('amount', 'percentage',)
    def _onchange_amount(self):
        """ Calculates the amount,percentage according to  amount or percentage selected"""
        if self.type == 'percentage':
            self.amount = self.percentage * self.budget_line_id.planned_amount / 100
            if self.budget_line_id.budget_type == 'earn' and self.percentage < 0:
                self.percentage = -self.percentage
        else:
            if self.budget_line_id.budget_type == 'spend' and self.amount > 0:
                self.amount = -self.amount
            elif self.budget_line_id.budget_type == 'earn' and self.amount < 0:
                self.amount = -self.amount
            self.percentage = self.amount * 100 / self.budget_line_id.planned_amount

    @api.constrains('amount', 'percentage')
    def _check_amount(self):
        """The constraints ensure that amount of the budget line is equal to the total of the category amount"""
        total = sum(self.search([('budget_line_id', '=', self.budget_line_id.id)]).mapped('amount'))
        total_planned = self.budget_line_id.planned_amount
        if self.budget_line_id.budget_type == 'spend':
            total = - total
            total_planned = -total_planned
        if total > total_planned:
            raise ValidationError("The Total of Amount Should not be greater than the Budget Line Amount ")
