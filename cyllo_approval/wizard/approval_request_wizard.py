# -*- coding: utf-8 -*-
from odoo import  fields, models

class ApprovalRequestWizard(models.TransientModel):
    _name = 'approval.request.wizard'
    _description = 'Approval Request Confirmation'

    rule_id = fields.Many2one('approval.rule', required=True)
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    def action_request_approval(self):
        """Create approval request from wizard."""
        Request = self.env['approval.request'].sudo()
        Request.create({
            'rule_id': self.rule_id.id,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'requested_by': self.env.user.id,
            'approver_id': self.rule_id.user_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
