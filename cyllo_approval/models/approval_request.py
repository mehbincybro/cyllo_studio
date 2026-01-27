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
from odoo import _, api, fields, models


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Approval requests"

    name = fields.Char(string='Request name')
    requested_by_id = fields.Many2one('res.users', help='Requested User')
    approval_rule_id = fields.Many2one('approval.rule',
                                       help="Rule Related to this approval")
    approver_ids = fields.Many2many('res.users', string='Approvers',
                                    default=lambda
                                        self: self._default_approvers(),
                                    help="The person who approves the request", )
    approved_by_id = fields.Many2one('res.users',
                                     help="The person who approved the request", )
    rejected_by_id = fields.Many2one('res.users',
                                     help="The person who rejected the request", )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('transferred', 'Transferred'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], string='State',
        copy=False, default="pending",
        help="Current status of the approval request")
    requested_date = fields.Datetime(help="Date when the request was made")
    approved_date = fields.Datetime(help="Date when the request was approved")
    model_name = fields.Char("Model Name")
    res_id = fields.Integer(string='Related Record Id',
                            help='The record ID for the Related Model')
    group_id = fields.Many2one('res.groups',
                               related='approval_rule_id.group_id')
    comment = fields.Text("Approval Comment", copy=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True,
                                 default=lambda self: self.env.company,
                                 help="Current company", tracking=True)
    read_by_ids = fields.Many2many(
        'res.users',
        'approval_request_read_by_rel', 'approval_request_id',
        'user_id',
        string='Read By Users',
        help="Users who have marked this approval request as read"
    )
    approval_transferred = fields.Boolean(
        related='approval_rule_id.transferred')

    @api.model
    def _default_approvers(self):
        """
        Populate default approvers based on the user_type of approval_rule_id.
        """
        approval_rule = self.env['approval.rule'].sudo().browse(
            self._context.get('default_approval_rule_id'))
        if not approval_rule:
            return []
        approvers = []
        if approval_rule.user_type == 'user':
            approvers.append(approval_rule.user_id.id)
        elif approval_rule.user_type == 'group':
            if approval_rule.group_id:
                group_users = approval_rule.group_id.users
                approvers.extend(group_users.ids)
        elif approval_rule.user_type == 'related':
            res = self.env[
                self._context.get('default_model_name')].sudo().browse(
                self._context.get('default_record_id'))
            if res:
                related_user = res[approval_rule.related_user_id.name]
                if related_user:
                    approvers.append(related_user.id)
        return [(6, 0, approvers)]

    @api.model
    def create(self, vals):
        """
        Overrides create to assign a formatted name to the approval request, schedule
        approval activities for approvers, and optionally send email notifications
        if enabled.
        """
        record = super(ApprovalRequest, self).create(vals)
        model_name = record.model_name
        res_id = vals.get('res_id')
        if model_name and res_id:
            related_record = self.env[model_name].browse(res_id)
            if related_record.exists():
                related_name = related_record.name
                sequence_number = record.id
                record.name = f"Req/{related_name}/{sequence_number:04d}"
        if record.approval_rule_id.email_notification:
            if record.approval_rule_id.notify_on_request and record.approver_ids:
                template = self.env.ref(
                    'cyllo_approval.mail_template_approval_request',
                    raise_if_not_found=False)
                if template:
                    template.send_mail(record.id, force_send=True)
        return record

    def write(self, vals):
        """
        Overrides write to handle approval/rejection state changes, schedule activity
        feedback, and send email notifications to the requester based on the approval
        or rejection status.
        """
        res = super(ApprovalRequest, self).write(vals)
        # Notify the requester via email when the  request is approved
        if 'state' in vals and vals['state'] == 'approved':
            for record in self:
                if record.approval_rule_id.email_notification:
                    if record.approval_rule_id.notify_on_approve:
                        template = self.env.ref(
                            'cyllo_approval.mail_template_request_approved')
                        if template:
                            template.send_mail(record.id, force_send=True)
        elif 'state' in vals and vals['state'] == 'rejected':
            for record in self:
                if record.approval_rule_id.email_notification:
                    if record.approval_rule_id.notify_on_reject:
                        template = self.env.ref(
                            'cyllo_approval.mail_template_request_rejected')
                        if template:
                            template.send_mail(record.id, force_send=True)
        return res

    def action_view_record(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model_name,
            'res_id': self.res_id,
            'target': 'current',
            'views': [(False, 'form')],
        }

    def action_approve(self):
        """
        Trigger the approval action on the related model's record based on
        the current approval request.
        """
        record = self.env[self.model_name].search(
            [('approval_request_id', '=', self.name)])
        return record.action_approve()

    def action_reject(self):
        """
        Trigger the reject action on the related model's record based on
        the current approval request.
        """
        record = self.env[self.model_name].search(
            [('approval_request_id', '=', self.name)])
        return record.action_reject()

    def action_forward(self):
        return {
            'name': _('Forward'),
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'approval.forward',
            'type': 'ir.actions.act_window',
            'context': {
                'default_approval_request_id': self.id,
                'default_from_user_ids': self.approver_ids.ids,
            }
        }

    def mark_as_read(self):
        """Mark the approval request as read for the current user"""
        current_user = self.env.user
        for record in self:
            if current_user not in record.read_by_ids:
                record.read_by_ids = [
                    (4, current_user.id)]

    def _get_approvers_emails(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        return ",".join([e for e in self.approver_ids.mapped("email") if e])