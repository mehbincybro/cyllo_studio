# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields

class TestApprovalModel(models.Model):
    _name = 'test.approval.model'
    _description = 'Test Approval Model'

    name = fields.Char(string="Name")
    approval_rule_id = fields.Many2one('approval.rule', string="Approval Rule")
    approval_request_id = fields.Many2one('approval.request', string="Approval Request")
    approval_request_ids = fields.One2many('approval.request', 'res_id', string="Approval Requests")
    approval_count = fields.Integer(string="Approval Count", compute="_compute_approval_count")
    can_approve = fields.Boolean(string="Can Approve", compute="_compute_can_approve")

    # --------------------------------------------------
    # Approval request creation
    # --------------------------------------------------
    def action_request_approval(self):
        approval = self.env['approval.request'].create({
            'res_model': self._name,
            'res_id': self.id,
            'requested_by_id': self.env.user.id,
            'state': 'draft',
        })
        self.approval_request_id = approval
        return {'params': {'type': 'success'}}

    # --------------------------------------------------
    # Compute approval count
    # --------------------------------------------------
    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = len(rec.approval_request_ids)

    # --------------------------------------------------
    # Compute can approve
    # --------------------------------------------------
    def _compute_can_approve(self):
        for rec in self:
            rec.can_approve = self.env.user == rec.approval_rule_id.user_id

    # --------------------------------------------------
    # Approve / Reject
    # --------------------------------------------------
    def action_approve(self):
        if not self.can_approve:
            return {'params': {'type': 'warning'}}
        self.approval_request_ids[-1].state = 'approved'

    def action_reject(self):
        self.approval_request_ids[-1].state = 'rejected'

    # --------------------------------------------------
    # Forward
    # --------------------------------------------------
    def action_forward(self):
        if not self.can_approve:
            return {'params': {'type': 'warning'}}
        return {'res_model': 'approval.forward'}

    # --------------------------------------------------
    # View approval requests
    # --------------------------------------------------
    def action_view_approval_request(self):
        return {
            'res_model': 'approval.request',
            'domain': [('res_id', '=', self.id)]
        }
