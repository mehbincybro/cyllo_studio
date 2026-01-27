# -*- coding: utf-8 -*-
from odoo import _, fields, models


class ProjectProject(models.Model):
    """ Model used to store budget details in project, perform budget related functions """
    _inherit = 'project.project'

    budget_id = fields.Many2one('budget.budget', 'Budget', help='The budget related to the Project')

    def action_view_budget(self):
        """This shows the budget related to the project in when clicking on the smart button"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget'),
            'res_model': 'budget.budget',
            'res_id': self.budget_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current'
        }
