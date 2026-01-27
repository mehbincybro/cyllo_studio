# -*- coding: utf-8 -*-
from odoo import _, fields, models


class BudgetBudget(models.Model):
    """ Model used to inherit budget.budget and adding project related functions """
    _inherit = 'budget.budget'

    project_id = fields.Many2one('project.project', help='Project related to budget')
    check_project = fields.Boolean(string='Project', help='True if the budget has a project')

    def action_view_project(self):
        """This shows the Project added/created from budget when click on the smart button"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project'),
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current'
        }
