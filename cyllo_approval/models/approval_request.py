# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import api, fields, models


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Request'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       index=True, default=lambda self: 'New')
    rule_id = fields.Many2one('approval.rule', required=True,
                              help="The approval rule that triggered this request.")
    company_id = fields.Many2one(related='rule_id.company_id', store=True, readonly=True,
                                 index=True)
    rule_type = fields.Selection(related='rule_id.rule_type',
                                 help="Type of rule (e.g., Condition, Always, etc.)")
    res_model = fields.Char(required=True, help="The technical name of the model being approved.")
    res_id = fields.Integer(required=True, help="The ID of the record being approved.")
    requested_by = fields.Many2one('res.users', string='Requested By',
                                   help="The user who initiated the approval request.")
    approver_id = fields.Many2one('res.users',
                                  help="The specific user assigned to approve this request.")
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending', help="Current state of the approval request.")
    is_used = fields.Boolean('Is Used', default=False,
                             help="Flag to indicate if this request has already been processed.")
    note = fields.Text('Note', help="Provide a reason for rejection or transfer.")
    can_approve = fields.Boolean(
        compute='_compute_can_approve',
        help="Technical field to check if the current user has permission to approve."
    )

    def _compute_can_approve(self):
        """Check if the current user is the approver or in the approver group."""
        is_manager = self.env.user.has_group('cyllo_approval.group_approval_manager')
        for record in self:
            is_approver = record.approver_id == self.env.user
            in_group = record.rule_id.group_id in self.env.user.groups_id
            record.can_approve = is_approver or in_group or is_manager

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('approval.request') or 'New'
        requests = super().create(vals_list)

        template = self.env.ref(
            'cyllo_approval.mail_template_approval_request')
        for request in requests:
            if request.rule_id.is_email_request:
                template.send_mail(request.id, force_send=True)
            model = request.res_model
            approval_record = self.env[model].browse(request.res_id)
            approval_record.x_approval_request_count += 1
            # Assign approval request linkApproval is required before changing the state. Please request approval.
            approval_record.write({
                'x_approval_request_ids': [
                    fields.Command.link(request.id)],
                'x_current_approver_id': request.rule_id.user_id.id,
                'x_current_group_id': request.rule_id.group_id.id,
            })
            # Mark approver field
            # if hasattr(rec, 'x_is_approver') and req.user_id:
            #     rec.write({'x_is_approver': req.user_id == self.env.user})
        return requests

    def action_approve(self):
        self.ensure_one()
        if not self.can_approve:
            raise models.ValidationError("You do not have permission to approve this request.")
        self.write({'state': 'approved',
                    'is_used': True,
                    })

        model = self.res_model
        approval_record = self.env[model].browse(self.res_id)
        approval_record.write({
            'x_approval_request_ids': [
                fields.Command.unlink(self.id)],
            'x_is_state_approval': False
        })
        if self.rule_id.is_email_approve:
            template = self.env.ref(
                'cyllo_approval.mail_template_request_approved')
            template.send_mail(self.id, force_send=True)

    def action_reject(self):
        self.ensure_one()
        if not self.can_approve:
            raise models.ValidationError("You do not have permission to reject this request.")
        self.write({'state': 'rejected',
                    'is_used': True,
                    })

        model = self.res_model
        approval_record = self.env[model].browse(self.res_id)
        approval_record.write({
            'x_approval_request_ids': [
                fields.Command.unlink(self.id)],
            'x_is_state_approval': False
        })
        if self.rule_id.is_email_reject:
            template = self.env.ref(
                'cyllo_approval.mail_template_request_rejected')
            template.send_mail(self.id, force_send=True)

    def action_transfer(self):
        self.ensure_one()
        if not self.can_approve:
            raise models.ValidationError("You do not have permission to transfer this request.")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_current_user_id': self.approver_id.id,
            },
        }

    def action_open_related_record(self):
        """Open the source document from the approval request."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "view_mode": "form",
            "res_id": self.res_id,
            "target": "current",
        }
