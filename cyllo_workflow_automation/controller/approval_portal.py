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
import json
import logging

from odoo import _, exceptions, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WorkflowApprovalPortal(http.Controller):
    """
    Public-facing portal for human approvers.

    URL: /workflow/approval/<token>

    The token is a UUID4 stored on workflow.approval.request. It is the
    ONLY piece of data in the URL — no record IDs or model names are
    exposed, preventing enumeration attacks.
    """

    # ------------------------------------------------------------------
    # GET  /workflow/approval/<token>   — display the approval form
    # ------------------------------------------------------------------

    @http.route(
        '/workflow/approval/<string:token>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def approval_page(self, token, **kwargs):
        """Render the approval decision page for the given token."""
        approval = self._get_valid_approval(token)
        if isinstance(approval, http.Response):
            return approval  # error page already built

        workflow_name = approval.workflow_id.name or 'Workflow Approval'
        approver_name = (
            approval.approver_name
            or (approval.approver_id.name if approval.approver_id else 'Approver')
        )

        return request.render('cyllo_workflow_automation.approval_portal_template', {
            'token': token,
            'approval': approval,
            'workflow_name': workflow_name,
            'approver_name': approver_name,
            'expiration': approval.expiration,
            'comment': approval.response_comment or '',
        })

    # ------------------------------------------------------------------
    # POST /workflow/approval/<token>/approve  — handle Approve action
    # POST /workflow/approval/<token>/reject   — handle Reject action
    # ------------------------------------------------------------------

    @http.route(
        '/workflow/approval/<string:token>/approve',
        type='http',
        auth='public',
        website=True,
        csrf=False,
        methods=['POST'],
    )
    def approval_approve(self, token, comment='', **kwargs):
        """Process an Approve action submitted from the portal form."""
        return self._handle_decision(token, 'approve', comment=comment)

    @http.route(
        '/workflow/approval/<string:token>/reject',
        type='http',
        auth='public',
        website=True,
        csrf=False,
        methods=['POST'],
    )
    def approval_reject(self, token, comment='', **kwargs):
        """Process a Reject action submitted from the portal form."""
        return self._handle_decision(token, 'reject', comment=comment)

    # ------------------------------------------------------------------
    # JSON endpoint for programmatic approval (internal/API use)
    # ------------------------------------------------------------------

    @http.route(
        '/workflow/approval/json/<string:token>',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def approval_json(self, token, decision, comment='', **kwargs):
        """
        JSON endpoint to approve or reject programmatically.

        Args:
            token (str): Approval token.
            decision (str): 'approve' or 'reject'.
            comment (str): Optional comment.

        Returns:
            dict: Result with ok flag and message.
        """
        approval = request.env['workflow.approval.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not approval:
            return {'ok': False, 'error': 'Invalid token.'}
        if approval.state != 'pending':
            return {'ok': False, 'error': f'Request is already {approval.state}.'}
        if approval.is_expired():
            approval.action_expire()
            return {'ok': False, 'error': 'Approval request has expired.'}
        if approval.token_used:
            return {'ok': False, 'error': 'This approval link has already been used.'}

        try:
            approval.consume_token()
            if decision == 'approve':
                approval.action_approve(comment=comment)
            elif decision == 'reject':
                approval.action_reject(comment=comment)
            else:
                return {'ok': False, 'error': f"Unknown decision: {decision!r}"}
            return {'ok': True, 'state': approval.state}
        except Exception as exc:
            _logger.error("Approval JSON endpoint error (token=%s): %s", token, exc)
            return {'ok': False, 'error': str(exc)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_valid_approval(self, token):
        """
        Look up and validate an approval request by token.

        Returns:
            WorkflowApprovalRequest | http.Response: the valid record or an error response.
        """
        approval = request.env['workflow.approval.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not approval:
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': _("This approval link is invalid or does not exist."),
                'token': token,
            })
        if approval.state != 'pending':
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'already_decided': True,
                'state': approval.state,
                'token': token,
                'workflow_name': approval.workflow_id.name or 'Workflow',
            })
        if approval.is_expired():
            approval.action_expire()
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'expired': True,
                'token': token,
                'workflow_name': approval.workflow_id.name or 'Workflow',
            })
        return approval

    def _handle_decision(self, token, decision, comment=''):
        """Process an approval/rejection decision and redirect to result page."""
        approver_ip = request.httprequest.remote_addr or ''
        approval = request.env['workflow.approval.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not approval:
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': _("This approval link is invalid."),
                'token': token,
            })
        if approval.state != 'pending':
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'already_decided': True,
                'state': approval.state,
                'token': token,
                'workflow_name': approval.workflow_id.name or 'Workflow',
            })
        if approval.is_expired():
            approval.action_expire()
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'expired': True,
                'token': token,
                'workflow_name': approval.workflow_id.name or 'Workflow',
            })
        if approval.token_used:
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': _("This approval link has already been used."),
                'token': token,
            })

        try:
            approval.consume_token()
            if decision == 'approve':
                approval.action_approve(comment=comment, approver_ip=approver_ip)
            else:
                approval.action_reject(comment=comment, approver_ip=approver_ip)
        except Exception as exc:
            _logger.error("Approval portal decision error (token=%s): %s", token, exc)
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': str(exc),
                'token': token,
            })

        return request.render('cyllo_workflow_automation.approval_portal_template', {
            'success': True,
            'decision': decision,
            'state': approval.state,
            'workflow_name': approval.workflow_id.name or 'Workflow',
            'token': token,
        })
