# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConsolidationChart(models.Model):
    """This model represents a consolidation chart that contains information about consolidated accounts, groups,
    and periods for financial reporting purposes"""
    _name = 'consolidation.chart'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Chart'

    name = fields.Char(string='Consolidation Name', required=True, help='Name of the consolidation chart')
    currency_id = fields.Many2one('res.currency', string="Target Currency", required=True,
                                  help='Select the target currency for consolidation')
    is_invert_sign = fields.Boolean(string='Invert Balance Sign', default=False,
                                    help='Check this if the balance sign should be inverted')
    company_ids = fields.Many2many('res.company', string='Companies',
                                   help='Companies associated with this consolidation chart')
    group_ids = fields.One2many('consolidation.group', 'chart_id', string='Account Groups',
                                help='Groups associated with this consolidation chart')
    account_ids = fields.One2many('consolidation.account', 'chart_id', string='Accounts',
                                  help='Accounts associated with this consolidation chart')
    period_ids = fields.One2many('consolidation.period', 'chart_id', string="Periods",
                                 help='Periods associated with this consolidation chart')
    group_ids_count = fields.Integer(string='Group Count', compute='_compute_group_ids_count',
                                     help='Count of account groups associated with this chart')
    account_ids_count = fields.Integer(string='Account Count', compute='_compute_account_ids_count',
                                       help='Count of accounts associated with this chart')
    period_ids_count = fields.Integer(string='Periods Count', compute='_compute_period_ids_count',
                                      help='Count of periods associated with this chart')
    is_currency_different = fields.Boolean(string='Different Currency', compute='_compute_is_currency_different',
                                           help='Indicates whether the currency is different or not.')

    @api.depends('company_ids', 'currency_id')
    def _compute_is_currency_different(self):
        """Compute method to determine if the targeted currency is different from company currencies."""
        for rec in self:
            if rec.company_ids.currency_id != rec.currency_id and rec.company_ids:
                rec.is_currency_different = True
            else:
                rec.is_currency_different = False

    @api.depends('group_ids')
    def _compute_group_ids_count(self):
        """Updates the 'group_ids_count' field with the count of account groups linked to this consolidation chart."""
        for rec in self:
            rec.group_ids_count = len(rec.group_ids)

    @api.depends('account_ids')
    def _compute_account_ids_count(self):
        """Updates the 'account_ids_count' field with the count of accounts linked to this consolidation chart."""
        for rec in self:
            rec.account_ids_count = len(rec.account_ids)

    @api.depends('period_ids')
    def _compute_period_ids_count(self):
        """Updates the 'period_ids_count' field with the count of periods linked to this consolidation chart."""
        for rec in self:
            rec.period_ids_count = len(rec.period_ids)

    def action_open_groups(self):
        """This action opens a window displaying the account groups associated with this chart."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Account Groups',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.group',
            'target': 'current',
            'domain': [('chart_id', '=', self.id)],
        }

    def action_open_accounts(self):
        """This action opens a window displaying the accounts associated with this chart."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidation Accounts',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.account',
            'target': 'current',
            'domain': [('chart_id', '=', self.id)],
        }

    def action_open_period(self):
        """This action opens a window displaying the periods associated with this chart."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Periods',
            'view_mode': 'tree,form',
            'res_model': 'consolidation.period',
            'target': 'current',
            'domain': [('chart_id', '=', self.id)],
        }
