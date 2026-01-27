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
from odoo import _, api, Command, fields, models
from odoo.exceptions import RedirectWarning


class CheckApproval(models.AbstractModel):
    _name = "check.approval"
    _description = "Check Approval"

    approval_request_id = fields.Many2one('approval.request')
    approval_rule_id = fields.Many2one('approval.rule')
    approval_rule_ids = fields.Many2many('approval.rule')
    show_request_button = fields.Boolean()
    approval_comment = fields.Text(copy=False)
    approval_transferred = fields.Boolean(
        related='approval_rule_id.transferred')
    server_trigger = fields.Boolean()
    allow_comment = fields.Boolean(related='approval_rule_id.allow_comment')
    approval_count = fields.Integer(compute="_compute_approval_count")
    approver_ids = fields.Many2many('res.users',
                                    related='approval_request_id.approver_ids')
    approval_request_ids = fields.Many2many('approval.request')
    can_approve = fields.Boolean(compute="_compute_can_approve")

    def _compute_approval_count(self):
        for record in self:
            approval_requests = self.env['approval.request'].search(
                [('model_name', '=', record._name), ('res_id', '=', record.id)])
            record.approval_count = len(approval_requests)

    @api.depends('approval_request_id', 'approval_request_id.approver_ids', 'approval_request_ids', 'approval_request_ids.state', 'approval_request_ids.approver_ids')
    def _compute_can_approve(self):
        for record in self:
            user = self.env.user
            is_manager = user.has_group('cyllo_approval.group_approval_manager')
            # Prefer the active Many2one request; fallback to a pending request from the M2M
            active_req = record.approval_request_id
            if not active_req and record.approval_request_ids:
                pending = record.approval_request_ids.filtered(lambda r: r.state == 'pending')
                active_req = pending[:1]
            has_request = bool(active_req)
            is_assigned = False
            if has_request:
                is_assigned = user.id in active_req.sudo().approver_ids.ids
            allowed = bool(has_request and (is_assigned or is_manager))
            record.can_approve = allowed

    def write(self, vals):
        if 'state' not in vals and 'stage_id' not in vals:
            return super().write(vals)
        current_model = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)], limit=1)
        approval_rules = self.env['approval.rule'].sudo().search(
            [('state', '=', 'enable'), ('model_id', '=', current_model.id)],
            order='sequence_order asc'
        )
        self.approval_rule_ids = [Command.clear()]
        notification_required = False
        for record in self:
            show_button = False
            for rec in approval_rules:
                approvers = self.env['res.users']
                if rec.user_id:
                    approvers |= rec.mapped('user_id')
                elif rec.group_id:
                    approvers |= rec.mapped('group_id.users')
                elif rec.related_user_id:
                    field_name = rec.related_user_id.name
                    if field_name in record._fields:
                        related_user = getattr(record, field_name, False)
                        if related_user:
                            approvers |= related_user
                if rec.definition_type == 'domain':
                    current_state_value = getattr(record, rec.state_value, None)
                    if record._fields[rec.state_value].type == 'many2one':
                        if str(current_state_value.id) == rec.sudo().state_from_id.value and \
                                str(vals.get(
                                    rec.state_value)) == rec.sudo().state_to_id.value:
                            if not record.approval_request_id:
                                domain_satisfy_models = self.search(
                                    rec._domain()).ids
                                if record.id in domain_satisfy_models:
                                    request_approvals = self.env[
                                        'approval.request'].search(
                                        [('approval_rule_id', '=', rec.id),
                                         ('model_name', '=', rec.model_select),
                                         ('res_id', '=', record.id), (
                                             'requested_by_id', '=',
                                             self.env.user.id),
                                         ('state', '=', 'approved')])
                                    if not request_approvals and self.env.user.id not in rec.approver_ids.ids:
                                        show_button = True
                                        vals.clear()
                                        vals['approval_rule_id'] = rec.id
                                        break
                            else:
                                if self.env.user.id not in rec.approver_ids.ids:
                                    vals.clear()
                                    notification_required = True
                    else:
                        if current_state_value == rec.sudo().state_from_id.value and \
                                vals.get(
                                    rec.state_value) == rec.sudo().state_to_id.value:
                            if not record.approval_request_id:
                                domain_satisfy_models = self.search(
                                    rec._domain()).ids
                                if record.id in domain_satisfy_models:
                                    request_approvals = self.env[
                                        'approval.request'].search(
                                        [('approval_rule_id', '=', rec.id),
                                         ('model_name', '=', rec.model_select),
                                         ('res_id', '=', record.id), (
                                             'requested_by_id', '=',
                                             self.env.user.id),
                                         ('state', '=', 'approved')])
                                    if not request_approvals and self.env.user.id not in rec.approver_ids.ids:
                                        show_button = True
                                        vals.clear()
                                        vals['approval_rule_id'] = rec.id
                                        break
                            else:
                                if self.env.user.id not in rec.approver_ids.ids:
                                    vals.clear()
                                    notification_required = True
            vals.update({'show_request_button': show_button})
            if show_button:
                notification_required = True
        result = super().write(vals)
        if not any([
            self.env.registry.ready is False,
        ]):
            self.env.cr.commit()
        reload_action = {'type': 'ir.actions.client', 'tag': 'reload'}
        if notification_required:
            raise RedirectWarning("Need an Approval for this Order",
                                  reload_action,
                                  _('Reload'))
        return result

    def action_approve(self):
        approval_requests = self.approval_request_ids.search(
            [('state', '=', 'pending')])
        if self.approval_request_id:
            if (self.env.user.id in self.approval_request_id.sudo().approver_ids.ids):
                self.approval_request_id.write({
                    'state': 'approved',
                    'comment': self.approval_comment,
                    'approved_by_id': self.env.user.id,
                    'approved_date': fields.Datetime.today().now(),
                })
                approval_requests = self.approval_request_ids.search(
                    [('state', '=', 'pending')])
                if approval_requests:
                    for request in approval_requests:
                        self.approval_request_id = request
                        if self.show_request_button:
                            self.show_request_button = False
                        break
                else:
                    self.approval_request_id = None
                    if self.server_trigger:
                        self.server_trigger = False
                    if self.show_request_button:
                        self.show_request_button = False
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Your not allowed to approve this record"),
                        'type': 'warning',
                    }
                }

    def action_reject(self):
        if self.approval_request_id:
            if (self.env.user.id in self.approval_request_id.sudo().approver_ids.ids):
                self.approval_request_id.write({
                    'state': 'rejected',
                    'comment': self.approval_comment,
                    'rejected_by_id': self.env.user.id,
                    'approved_date': fields.Datetime.today().now(),
                })
                self.approval_request_id = None
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Your not allowed to reject this record"),
                        'type': 'warning',
                    }
                }

    def action_forward(self):
        if not (self.env.user.has_group(
                'cyllo_approval.group_approval_manager') or self.env.user.id in self.approval_request_id.approver_ids.ids):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("You are not allowed to transfer the request"),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'name': _('Forward'),
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'approval.forward',
            'type': 'ir.actions.act_window',
            'context': {
                'default_approval_request_id': self.approval_request_id.id,
                'default_from_user_ids': self.approval_request_id.approver_ids.ids,
            }
        }

    def action_request_approval(self):
        approval_rule = self.approval_rule_id
        if approval_rule:
            new_request = self.env['approval.request'].with_context(
                default_approval_rule_id=approval_rule.id,
                default_model_name=self._name,
                default_record_id=self.id,
            ).create({
                'approval_rule_id': approval_rule.id,
                'model_name': self._name,
                'requested_by_id': self.env.user.id,
                'requested_date': fields.Datetime.today().now(),
                'res_id': self.id,
            })
            self.approval_request_id = new_request
            self.write({
                'approval_request_ids': [(4, new_request.id)]
            })

            self.show_request_button = False
            next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "Request Sent Successfully",
                    'type': 'success',
                    'sticky': False,
                    'next': next_action
                },
            }

    def action_view_approval_request(self):
        approval_requests = self.env['approval.request'].search(
            [('model_name', '=', self._name), ('res_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Requests',
            'res_model': 'approval.request',
            'target': 'current',
            'view_mode': 'tree',
            'domain': [('id', 'in', approval_requests.ids)],
        }
