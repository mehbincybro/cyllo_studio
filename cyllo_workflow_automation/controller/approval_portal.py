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
from odoo import _, exceptions, http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WorkflowApprovalPortal(http.Controller):

    @http.route(
        '/workflow/approval/<string:token>',
        type='http',
        auth='public',
        website=True,
        csrf=False,
    )
    def approval_page(self, token, **kwargs):
        node = request.env['node.struct'].sudo().search([('approval_token', '=', token)], limit=1)
        if not node or not node.approval_request_id:
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': _("This approval link is invalid or has expired."),
                'token': token,
            })
            
        approval = request.env['approval.request'].sudo().browse(node.approval_request_id)
        if not approval.exists() or approval.state != 'pending':
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'already_decided': True,
                'state': approval.state,
                'token': token,
                'workflow_name': node.approval_resume_work_auto_id.name or 'Workflow',
            })
            
        return request.render('cyllo_workflow_automation.approval_portal_template', {
            'token': token,
            'approval': approval,
            'workflow_name': node.approval_resume_work_auto_id.name or 'Workflow',
            'approver_name': approval.approver_id.name if approval.approver_id else 'Approver',
            'comment': '',
        })

    @http.route(
        '/workflow/approval/<string:token>/approve',
        type='http',
        auth='public',
        website=True,
        csrf=False,
        methods=['POST'],
    )
    def approval_approve(self, token, comment='', **kwargs):
        return self._handle_decision(token, 'approved', comment=comment)

    @http.route(
        '/workflow/approval/<string:token>/reject',
        type='http',
        auth='public',
        website=True,
        csrf=False,
        methods=['POST'],
    )
    def approval_reject(self, token, comment='', **kwargs):
        return self._handle_decision(token, 'rejected', comment=comment)

    def _handle_decision(self, token, decision, comment=''):
        node = request.env['node.struct'].sudo().search([('approval_token', '=', token)], limit=1)
        if not node or not node.approval_request_id:
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'error': _("This approval link is invalid or has expired."),
                'token': token,
            })
            
        approval = request.env['approval.request'].sudo().browse(node.approval_request_id)
        if not approval.exists() or approval.state != 'pending':
            return request.render('cyllo_workflow_automation.approval_portal_template', {
                'already_decided': True,
                'state': approval.state,
                'token': token,
                'workflow_name': node.approval_resume_work_auto_id.name or 'Workflow',
            })

        # Directly approve/reject bypassing can_approve (since it's via public portal token)
        approval.sudo().write({
            'state': decision,
            'is_used': True,
            'note': comment,
        })
        
        # Resume workflow
        node._approval_resume(decision, approval_comment=comment or '')

        return request.render('cyllo_workflow_automation.approval_portal_template', {
            'success': True,
            'decision': decision,
            'state': decision,
            'workflow_name': node.approval_resume_work_auto_id.name or 'Workflow',
            'token': token,
        })
