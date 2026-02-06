# -*- coding: utf-8 -*-
from odoo import api,fields, models

class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Request'

    rule_id = fields.Many2one('approval.rule', required=True)
    rule_type = fields.Selection(related='rule_id.rule_type')
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    requested_by = fields.Many2one('res.users', string='Requested By')
    approver_id = fields.Many2one('res.users')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    is_used = fields.Boolean('Is Used',default=False)

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)

        template = self.env.ref(
            'cyllo_approval.mail_template_approval_request')
        for request in requests:
            if request.rule_id.is_email_request:
                template.send_mail(request.id, force_send=True)
            model = request.res_model
            approval_record = self.env[model].browse(request.res_id)
            approval_record.x_approval_request_count += 1
            # 🔗 Assign approval request link
            approval_record.write({
                'x_approval_request_ids': [
                    fields.Command.link(request.id)],
                'x_current_approver_id': request.rule_id.user_id.id,
                'x_current_group_id': request.rule_id.group_id.id,
            })
            # 👤 Mark approver field
            # if hasattr(rec, 'x_is_approver') and req.user_id:
            #     rec.write({'x_is_approver': req.user_id == self.env.user})
        return requests

    def action_approve(self):
        self.ensure_one()
        self.write({'state': 'approved',
                    'is_used' : True,
                    })

        model = self.res_model
        approval_record = self.env[model].browse(self.res_id)
        approval_record.write({
            'x_approval_request_ids': [
            fields.Command.unlink(self.id)],
            'x_is_state_approval' : False
        })
        if self.rule_id.is_email_approve:
            template = self.env.ref(
                'cyllo_approval.mail_template_request_approved')
            template.send_mail(self.id, force_send=True)

    def action_reject(self):
        self.ensure_one()
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
