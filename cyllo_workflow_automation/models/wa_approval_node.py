# -*- coding: utf-8 -*-
import uuid
import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class WaApprovalNodeMixin(models.AbstractModel):
    _name = 'wa.approval.node.mixin'
    _description = 'Workflow Approval Node Mixin'

    @api.model
    def execute(self, node_id, work_auto_id, record):
        """
        Called from generated workflow code on every execution pass.

        On the FIRST pass (no resume):
          - Evaluates auto-approve rule.
          - Creates the approval.request record.
          - Sends notifications.
          - Returns 'paused' → workflow stops.

        On RESUME (decision already made):
          - Returns the approval_branch string ('approved'/'rejected'/'timeout')
            so the generated if/elif dispatch routes to the correct port.

        The resume check reads self.env.context because _run_from_node creates
        the eval `env` via with_context(__approval_resume__=True, ...).
        """
        # Resume path
        if self.env.context.get('__approval_resume__'):
            return self.env.context.get('approval_branch', 'approved')

        # Check if cyllo_approval module is installed (models exist)
        if 'approval.request' not in self.env:
            _logger.warning("WaApprovalNodeMixin: 'cyllo_approval' module is not installed. Skipping Approval node.")
            return 'approved'

        # We are pausing. Let's find the NodeStruct.
        node = self.env['node.struct'].sudo().search([
            ('work_auto_id', '=', work_auto_id),
            ('id', '=', int(node_id))
        ], limit=1)

        if not node:
            _logger.error("WaApprovalNodeMixin: NodeStruct not found for workflow %s, nodeId %s", work_auto_id, node_id)
            return 'paused'

        # Resolve Approver
        approver = False
        if node.approval_approver_type == 'user' and node.approval_approver_id:
            approver = node.approval_approver_id
        elif node.approval_approver_type == 'group' and node.approval_approver_group_id:
            approver = node.approval_approver_group_id.users[:1]
        elif node.approval_approver_type == 'dynamic' and node.approval_approver_field:
            try:
                # Evaluate dynamic field. `record` is passed to the execution environment.
                safe_env = {'record': record, 'env': self.env}
                approver = eval(node.approval_approver_field, safe_env)
            except Exception as e:
                _logger.error("WaApprovalNodeMixin: Error evaluating approver field %s: %s", node.approval_approver_field, e)

        # Setup Auto Rule check
        if node.approval_auto_rule:
            try:
                safe_env = {'record': record, 'env': self.env}
                if eval(node.approval_auto_rule, safe_env):
                    # Auto approved
                    if node.approval_result_variable:
                        # Write the variable to context or similar if needed.
                        # For simple execution, we just return the branch and the generator handles the var.
                        pass
                    return 'approved'
            except Exception as e:
                _logger.error("WaApprovalNodeMixin: Error evaluating auto rule %s: %s", node.approval_auto_rule, e)

        # Resolve or create rule
        rule_id = node.approval_rule_id
        rule = self.env['approval.rule'].sudo().browse(rule_id) if rule_id else self.env['approval.rule']
        if not rule.exists():
            # create one automatically on the fly if missing
            rule_name = node.approval_subject or f"Workflow Approval {work_auto_id}"
            rule = self.env['approval.rule'].sudo().create({
                'name': rule_name,
                'model_id': self.env['ir.model']._get(record._name).id,
                'rule_type': 'server',
                'user_id': approver.id if approver else False,
                'is_email_request': node.approval_notify_email,
                'is_email_approve': False,
                'is_email_reject': False,
            })
            node.approval_rule_id = rule.id

        # Generate Secure Token
        token = str(uuid.uuid4())
        
        # Create Request
        request_vals = {
            'rule_id': rule.id,
            'res_model': record._name,
            'res_id': record.id,
            'approver_id': approver.id if approver else False,
            'requested_by': self.env.uid,
        }
        approval_req = self.env['approval.request'].sudo().create(request_vals)
        
        # Update node state for resumption
        node.write({
            'approval_token': token,
            'approval_request_id': approval_req.id,
            'approval_resume_work_auto_id': work_auto_id,
            'approval_resume_record_model': record._name,
            'approval_resume_record_id': record.id,
            'approval_draw_node_id': str(node_id),
        })

        # Send Notifications
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        approval_url = f"{base_url}/workflow/approval/{token}"
        subject = node.approval_subject or "Your Approval is Required"

        if node.approval_notify_email and approver and approver.email:
            body = (
                f"<p>Hello {approver.name},</p>"
                f"<p>Your approval is required: <strong>{subject}</strong></p>"
                f"<p><a href=\"{approval_url}\" style=\"background:#875a7b;color:white;padding:8px 20px;border-radius:4px;text-decoration:none;\">Review &amp; Approve</a></p>"
            )
            self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body,
                'email_to': approver.email,
            }).send()

        if node.approval_notify_inbox and approver and approver.partner_id:
            try:
                self.env['mail.message'].sudo().create({
                    'message_type': 'notification',
                    'partner_ids': [(4, approver.partner_id.id)],
                    'subject': subject,
                    'body': f'Approval required: {subject}<br/><a href="{approval_url}">Open Approval Request</a>',
                })
            except Exception as e:
                _logger.warning("WaApprovalNodeMixin: Inbox notification failed: %s", e)

        # Setup Timeout Cron if needed
        if node.approval_timeout_hours > 0:
            cron_name = f"Workflow Approval Timeout {node.id}"
            nextcall = fields.Datetime.now() + relativedelta(hours=node.approval_timeout_hours)
            cron = self.env['ir.cron'].sudo().create({
                'name': cron_name,
                'model_id': self.env['ir.model']._get('node.struct').id,
                'state': 'code',
                'code': f"model.browse({node.id})._approval_timeout()",
                'interval_number': 1,
                'interval_type': 'days',
                'numbercall': 1,
                'nextcall': nextcall,
                'active': True,
            })
            node.approval_timeout_cron_id = cron.id

        return 'paused'

class NodeStructApprovalMixin(models.Model):
    _inherit = 'node.struct'

    def _approval_timeout(self):
        """Called by the timeout cron."""
        for node in self:
            if not node.approval_request_id:
                continue
            
            request = self.env['approval.request'].sudo().browse(node.approval_request_id)
            if not request.exists() or request.state != 'pending':
                continue
            
            # Reject request
            request.write({
                'state': 'rejected',
                'is_used': True,
                'note': 'Auto-rejected due to timeout.'
            })
            
            # Resume workflow
            node._approval_resume('timeout', approval_comment='Auto-rejected due to timeout.')

    def _approval_resume(self, decision, approval_comment=''):
        """
        Called when a decision is made (approved, rejected) or timeout occurs.
        Resumes the paused workflow from the approval node with the correct branch.
        """
        self.ensure_one()

        if not self.approval_resume_work_auto_id:
            return False

        workflow = self.approval_resume_work_auto_id

        # Pass trigger_type from the stored work.auto record so the trigger
        # guard in the compiled code (`if trigger_type == 'create':`) passes.
        resume_trigger = workflow.trigger_type or ''

        workflow.with_context(
            __approval_resume__=True,
            approval_branch=decision,
            approval_comment=approval_comment,
            trigger_type=resume_trigger,
        )._run_from_node(
            self.approval_draw_node_id,
            self.approval_resume_record_model,
            self.approval_resume_record_id,
            decision,
            approval_comment=approval_comment,
        )

        # Cleanup
        if self.approval_timeout_cron_id:
            self.approval_timeout_cron_id.unlink()
        
        self.write({
            'approval_token': False,
            'approval_resume_work_auto_id': False,
            'approval_resume_record_model': False,
            'approval_resume_record_id': False,
        })
        return True
