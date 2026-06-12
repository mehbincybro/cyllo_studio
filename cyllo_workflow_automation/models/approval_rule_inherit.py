# -*- coding: utf-8 -*-
from odoo import fields, models

class ApprovalRule(models.Model):
    _inherit = 'approval.rule'

    work_auto_id = fields.Many2one('work.auto', string="Linked Workflow Automation", ondelete="cascade",
                                   help="The workflow automation that manages this rule.")
