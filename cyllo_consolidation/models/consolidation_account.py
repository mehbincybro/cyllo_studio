# -*- coding: utf-8 -*-
from odoo import fields, models


class ConsolidationAccount(models.Model):
    """This model handles the creation and management of consolidation
    accounts"""
    _name = 'consolidation.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Account'

    name = fields.Char(string='Account Name', required=True, help='Name of the consolidation account')
    view_name = fields.Char(string='Account Name', compute='_compute_view_name', help='Displayed name of the account')
    chart_id = fields.Many2one('consolidation.chart', string='Consolidation',
                               help='Select the consolidation chart associated with this account.')
    is_invert_sign = fields.Boolean(string='Invert Balance Sign', default=False,
                                    help='Check this if the balance sign should be inverted')
    group_id = fields.Many2one('consolidation.group',
                               help='Select the group associated with this consolidation account.')
    account_ids = fields.Many2many('account.account', string="Accounts", help='Associated accounts')

    def _compute_view_name(self):
        """Compute the displayed name of the account based on group and name."""
        for record in self:
            record.view_name = record.name
            if record.group_id and record.group_id.group_id:
                record.view_name = f'{record.group_id.view_name} /{record.name}'
            elif record.group_id:
                record.view_name = f'{record.group_id.name} /{record.name}'
