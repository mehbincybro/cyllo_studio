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

# Standard library
import logging
import secrets
from datetime import timedelta

# Odoo framework
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _approval_module_installed(env):
    """Check whether cyllo_approval is installed in the current environment.

    Args:
        env (odoo.api.Environment): The Odoo environment.

    Returns:
        bool: True if cyllo_approval is installed and approval.rule model exists.
    """
    return 'approval.rule' in env and 'approval.request' in env


class WaApprovalNodeMixin(models.AbstractModel):
    """Workflow Approval Node execution mixin.

    Provides the execute() method called from generated workflow code when
    an Approval node is reached. Handles:

    - Auto-approve rule evaluation (skip human step if expression is True)
    - Finding or creating an approval.request via the configured approval.rule
    - Sending notification email via the rule's email settings
    - Pausing the workflow (returning 'paused' on first pass)
    - Resuming on the correct branch when the approval is resolved

    On RESUME (when _run_from_node re-executes the code with
    __approval_resume__=True in context):
      - Returns the stored approval_branch so the if/elif dispatch works.

    Used by: cyllo_workflow_automation
    Depends on: cyllo_approval (optional — guarded by _approval_module_installed)
    """

    _name = 'wa.approval.node.mixin'
    _description = 'Workflow Approval Node Mixin'

    @api.model
    def execute(self, node_id, work_auto_id, record):
        """Execute the Approval node for a given workflow pass.

        On the first pass (no __approval_resume__ in context):
          1. Evaluate auto-approve expression — if True, return 'approved'.
          2. Ensure cyllo_approval is installed.
          3. Find the node.struct and its configured approval.rule.
          4. Create an approval.request record (visible in Approval module).
          5. Store pause state on node.struct.
          6. Optionally schedule a timeout ir.cron.
          7. Return 'paused' so the generated code does `pass` (stops execution).

        On resume (__approval_resume__=True in context):
          Return context['approval_branch'] ('approved'/'rejected'/'timeout')
          so the elif dispatch in the generated code routes to the right port.

        Args:
            node_id (int): ID of the node.struct record for this Approval node.
            work_auto_id (int): ID of the work.auto being executed.
            record (recordset): The triggering record (may be empty on resume).

        Returns:
            str: 'paused', 'approved', 'rejected', or 'timeout'.
        """
        # ── Resume path ───────────────────────────────────────────────────────
        if self.env.context.get('__approval_resume__'):
            return self.env.context.get('approval_branch', 'approved')

        # ── Approval module guard ─────────────────────────────────────────────
        if not _approval_module_installed(self.env):
            _logger.warning(
                "WaApprovalNodeMixin.execute: cyllo_approval not installed — "
                "auto-approving node %s.", node_id
            )
            return 'approved'

        # ── Load node.struct ──────────────────────────────────────────────────
        node = self.env['node.struct'].sudo().browse(int(node_id))
        if not node.exists():
            _logger.error(
                "WaApprovalNodeMixin.execute: node.struct #%s not found.", node_id
            )
            return 'approved'

        # ── Auto-approve rule ─────────────────────────────────────────────────
        if node.approval_auto_rule and (node.approval_auto_rule or '').strip():
            try:
                from odoo.tools.safe_eval import safe_eval
                result = safe_eval(
                    node.approval_auto_rule.strip(),
                    {'record': record, 'env': self.env},
                )
                if result:
                    _logger.info(
                        "Approval node #%s auto-approved (rule=%s).",
                        node_id, node.approval_auto_rule
                    )
                    return 'approved'
            except Exception as exc:
                _logger.error(
                    "Approval node #%s auto-approve eval error: %s", node_id, exc
                )

        # ── Resolve approval.rule ─────────────────────────────────────────────
        rule = self._resolve_approval_rule(node, record, work_auto_id)
        if not rule:
            _logger.error(
                "Approval node #%s: no approval.rule found or created — auto-approving.",
                node_id
            )
            return 'approved'

        # ── Resolve approver ──────────────────────────────────────────────────
        approver = self._resolve_approver(node, rule, record)

        # ── Create approval.request ───────────────────────────────────────────
        # This creates a real approval.request visible in the Approval module.
        approval_request = self.env['approval.request'].sudo().create({
            'rule_id': rule.id,
            'res_model': record._name,
            'res_id': record.id,
            'requested_by': self.env.uid,
            'approver_id': approver.id if approver else rule.user_id.id,
            'state': 'pending',
        })

        # ── Persist pause state on node.struct ───────────────────────────────
        node.sudo().write({
            'approval_request_id': approval_request.id,
            'approval_resume_work_auto_id': work_auto_id,
            'approval_resume_record_model': record._name,
            'approval_resume_record_id': record.id,
            'approval_draw_node_id': str(node_id),
        })

        # ── Schedule timeout cron ─────────────────────────────────────────────
        timeout_h = node.approval_timeout_hours or node.approval_expire_after or 0.0
        if timeout_h > 0:
            self._schedule_timeout_cron(node, work_auto_id, timeout_h)

        _logger.info(
            "Workflow #%s paused at Approval node #%s — request #%s created.",
            work_auto_id, node_id, approval_request.id
        )
        return 'paused'

    # ── Internal helpers ──────────────────────────────────────────────────────

    @api.model
    def _resolve_approval_rule(self, node, record, work_auto_id):
        """Find or create the approval.rule for this Approval node.

        Uses node.approval_rule_id (stored as integer) if set. Otherwise
        looks for an existing server-type rule matching the model, or creates
        one automatically.

        Args:
            node (node.struct): The Approval node record.
            record (recordset): The triggering record.
            work_auto_id (int): The work.auto ID.

        Returns:
            approval.rule | False: The resolved or created rule.
        """
        ApprovalRule = self.env['approval.rule'].sudo()

        # Prefer explicitly configured rule
        if node.approval_rule_id:
            rule = ApprovalRule.browse(int(node.approval_rule_id))
            if rule.exists():
                return rule

        # Auto-create a server-type rule bound to this model
        model_rec = self.env['ir.model'].sudo().search(
            [('model', '=', record._name)], limit=1
        )
        if not model_rec:
            return False

        # Look for existing auto-created rule for this workflow node
        rule_name = _('Workflow Approval: %s [node#%s]') % (
            self.env['work.auto'].sudo().browse(work_auto_id).name or '',
            node.id,
        )
        rule = ApprovalRule.search([
            ('name', '=', rule_name),
            ('model_id', '=', model_rec.id),
        ], limit=1)

        rule_type = node.approval_rule_type or 'server'
        approver_user = self._resolve_approver(node, None, record)
        
        vals = {
            'name': rule_name,
            'model_id': model_rec.id,
            'rule_type': rule_type,
            'user_id': approver_user.id if approver_user else self.env.uid,
            'is_email': node.approval_notify_email,
            'is_email_request': node.approval_notify_on_request,
            'is_email_approve': node.approval_notify_on_approve,
            'is_email_reject': node.approval_notify_on_reject,
            'is_comment': node.approval_allow_comment,
        }
        
        if rule_type == 'button' and node.approval_button_id:
            vals['button_id'] = node.approval_button_id
        elif rule_type == 'server' and node.approval_server_action_id:
            vals['server_action_id'] = node.approval_server_action_id
        elif rule_type == 'state' and node.approval_state_field_id:
            vals['state_field_id'] = node.approval_state_field_id
            if node.approval_state_to_selection_id:
                vals['state_to_selection_id'] = node.approval_state_to_selection_id
            if node.approval_state_to_m2o_value_id:
                vals['state_to_m2o_value_id'] = node.approval_state_to_m2o_value_id

        if rule:
            rule.write(vals)
        else:
            rule = ApprovalRule.create(vals)
            # Persist the rule ID back onto the node so it's reused
            node.sudo().write({'approval_rule_id': rule.id})

        return rule

    @api.model
    def _resolve_approver(self, node, rule, record):
        """Resolve the approver res.users record for this node.

        Priority:
          1. approver_type == 'user'  → node.approval_approver_id
          2. approver_type == 'group' → first user of node.approval_approver_group_id
          3. approver_type == 'dynamic' → eval node.approval_approver_field
          4. Fallback to rule.user_id if rule is provided

        Args:
            node (node.struct): The Approval node.
            rule (approval.rule | None): The resolved rule (may be None).
            record (recordset): The triggering record.

        Returns:
            res.users | False
        """
        atype = node.approval_approver_type or 'user'

        if atype == 'user' and node.approval_approver_id:
            return node.approval_approver_id

        if atype == 'group' and node.approval_approver_group_id:
            users = node.approval_approver_group_id.users
            return users[:1] if users else False

        if atype == 'dynamic' and (node.approval_approver_field or '').strip():
            try:
                from odoo.tools.safe_eval import safe_eval
                result = safe_eval(
                    node.approval_approver_field.strip(),
                    {'record': record, 'env': self.env},
                )
                if result and hasattr(result, '_name') and result._name == 'res.users':
                    return result[:1]
            except Exception as exc:
                _logger.error(
                    "Approval node #%s dynamic approver eval error: %s",
                    node.id, exc
                )

        if rule and rule.user_id:
            return rule.user_id

        return False

    @api.model
    def _schedule_timeout_cron(self, node, work_auto_id, timeout_hours):
        """Create a one-shot ir.cron to auto-reject after timeout_hours.

        Args:
            node (node.struct): The Approval node.
            work_auto_id (int): The work.auto ID.
            timeout_hours (float): Hours until auto-rejection.

        Returns:
            None
        """
        nextcall = fields.Datetime.now() + timedelta(hours=float(timeout_hours))
        model_rec = self.env['ir.model'].sudo().search(
            [('model', '=', 'node.struct')], limit=1
        )
        cron = self.env['ir.cron'].sudo().create({
            'name': 'WF Approval Timeout [node#%s / wa#%s]' % (node.id, work_auto_id),
            'model_id': model_rec.id,
            'state': 'code',
            'code': 'model.browse(%d)._approval_timeout()' % node.id,
            'interval_number': 1,
            'interval_type': 'minutes',
            'numbercall': 1,
            'nextcall': nextcall,
            'active': True,
        })
        node.sudo().write({'approval_timeout_cron_id': cron.id})


class NodeStructApprovalMixin(models.Model):
    """Extend node.struct with approval resume and timeout methods.

    Patches approval.request.write() once at module load so that when
    an approver clicks Approve/Reject in the Approval module UI, the
    corresponding workflow branch is triggered automatically.

    Used by: cyllo_workflow_automation
    Inherits: node.struct
    """

    _inherit = 'node.struct'

    def _register_hook(self):
        """Patch approval.request.write once to intercept state changes.

        This is the same pattern used for Button and State-change rules in
        cyllo_approval's _patch_method(). It hooks into approval.request
        state transitions so the workflow resumes when a decision is made
        from the Approval module's UI (not just via email URL).
        """
        super()._register_hook()

        if not _approval_module_installed(self.env):
            return

        ApprovalRequest = self.env['approval.request'].__class__
        if getattr(ApprovalRequest, '_wa_workflow_patched', False):
            return

        ApprovalRequest._wa_workflow_patched = True
        _original_write = ApprovalRequest.write

        def _patched_write(self_req, vals):
            """Intercept state changes and resume paused workflow nodes."""
            result = _original_write(self_req, vals)
            new_state = vals.get('state')
            if new_state in ('approved', 'rejected'):
                for req in self_req:
                    nodes = self_req.env['node.struct'].sudo().search([
                        ('approval_request_id', '=', req.id),
                        ('approval_resume_work_auto_id', '!=', False),
                    ])
                    for node in nodes:
                        node._approval_resume(new_state)
            return result

        ApprovalRequest.write = _patched_write

    def _approval_timeout(self):
        """Called by the timeout ir.cron to auto-reject the pending request.

        Finds the approval.request linked to this node, rejects it, and
        resumes the workflow on the Timeout branch (output_3).

        Returns:
            None
        """
        self.ensure_one()
        if not self.approval_request_id:
            return

        if not _approval_module_installed(self.env):
            return

        req = self.env['approval.request'].sudo().browse(self.approval_request_id)
        if not req.exists() or req.state != 'pending':
            # Already resolved — cron is stale
            return

        req.write({
            'state': 'rejected',
            'is_used': True,
        })

        self._approval_resume('timeout', comment='Auto-rejected: approval timed out.')

    def _approval_resume(self, decision, comment=''):
        """Resume the paused workflow on the correct output branch.

        Called from:
          - NodeStructApprovalMixin._register_hook (patched write)
          - _approval_timeout (cron)

        Args:
            decision (str): 'approved', 'rejected', or 'timeout'.
            comment (str): Optional approval comment.

        Returns:
            bool: True if resumed, False if nothing to resume.
        """
        self.ensure_one()
        if not self.approval_resume_work_auto_id:
            return False

        workflow = self.approval_resume_work_auto_id
        resume_trigger = workflow.trigger_type or ''

        workflow.with_context(
            __approval_resume__=True,
            approval_branch=decision,
            approval_comment=comment,
            trigger_type=resume_trigger,
        )._run_from_node(
            node_id=self.approval_draw_node_id,
            record_model=self.approval_resume_record_model,
            record_id=self.approval_resume_record_id,
            approval_branch=decision,
            approval_comment=comment,
        )

        # Cancel timeout cron if still active and decision was not timeout
        if decision != 'timeout' and self.approval_timeout_cron_id:
            try:
                self.approval_timeout_cron_id.sudo().write({'active': False})
            except Exception:
                pass
            self.sudo().write({'approval_timeout_cron_id': False})

        # Clear resume state so a second click is ignored
        self.sudo().write({
            'approval_resume_work_auto_id': False,
            'approval_resume_record_model': False,
            'approval_resume_record_id': False,
        })

        return True
