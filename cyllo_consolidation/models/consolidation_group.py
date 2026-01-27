# -*- coding: utf-8 -*-
from odoo import fields, models


class ConsolidationGroup(models.Model):
    """This model represents groups used for categorizing consolidation accounts
    within a consolidation chart."""
    _name = 'consolidation.group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Account Group'
    _rec_name = 'view_name'

    name = fields.Char(string='Group Name', required=True, help='Name of the account group')
    view_name = fields.Char(string='Account Group', compute='_compute_view_name',
                            help='Displayed name of the account group')
    chart_id = fields.Many2one('consolidation.chart', string='Consolidation',
                               help='Associated consolidation chart')
    group_id = fields.Many2one('consolidation.group', string='Parent',
                               help='Parent group of this account group')
    group_ids = fields.One2many('consolidation.group', 'group_id', string='Children',
                                help='Children groups under this group')
    account_ids = fields.One2many('consolidation.account', 'group_id',
                                  string='Consolidation Accounts', help='Accounts associated with this group')

    def _compute_view_name(self):
        """This method constructs the view name for the account group based on
        its associated parent group and its own name."""
        for record in self:
            if record.group_id:
                record.view_name = f'{record.group_id.name} /{record.name}'
            else:
                record.view_name = record.name
