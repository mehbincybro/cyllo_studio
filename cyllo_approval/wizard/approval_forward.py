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
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ApprovalForward(models.TransientModel):
    _name = "approval.forward"
    _description = "Approval Forward"

    from_user_ids = fields.Many2many(
        'res.users',
        'approval_forward_from_users_rel',
        'request_id',
        'user_id',
        string="From"
    )
    approval_request_id = fields.Many2one('approval.request')
    approver_ids = fields.Many2many(
        'res.users',
        'approval_forward_approvers_rel',
        'request_id',
        'user_id',
        compute="_compute_approver_ids",
    )
    to_user_ids = fields.Many2many(
        'res.users',
        'approval_forward_to_users_rel',
        'request_id',
        'user_id',
        string="To",
    )

    @api.depends('approval_request_id')
    def _compute_approver_ids(self):
        approvers = self.env['res.users']
        model_name = self.env.context.get('active_model', [])
        users = self.env['res.users'].search([('active', '=', True)])
        for record in self:
            if model_name:
                target_record = self.env[model_name].sudo().browse(self.env.context.get('active_id'))
                for user in users:
                    try:
                        if target_record.with_user(user).check_access_rights(
                                'write', raise_exception=False):
                            try:
                                target_record.with_user(user).check_access_rule(
                                    'write')
                                approvers |= user
                            except Exception:
                                continue
                    except Exception as e:
                        _logger.debug(
                            f"Access check failed for user {user.name}: {str(e)}")
                        continue
                record.approver_ids = approvers
            else:
                record.approver_ids = approvers

    def action_confirm_forward(self):
        if not self.to_user_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Select the user to whom the request will be transferred"),
                    'type': 'warning',
                }
            }
        if set(self.to_user_ids.ids) & set(self.from_user_ids.ids):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "The 'From' user and 'To' user cannot be the same. Please choose different users."),
                    'type': 'warning',
                    'sticky': False,
                }
            }
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
        if self.approval_request_id:
            self.approval_request_id.approver_ids = self.to_user_ids
            self.approval_request_id.write({'state': 'transferred'})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _(
                        "Request Transferred Successfully"),
                    'type': 'success',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }