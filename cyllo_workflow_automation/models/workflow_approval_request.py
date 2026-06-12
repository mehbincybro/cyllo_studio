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
import uuid
import logging

from odoo import _, api, exceptions, fields, models

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exception used to pause workflow execution at an Approval node.
# Raised inside generated workflow code; caught by the engine to persist state.
# ---------------------------------------------------------------------------


class WorkflowApprovalPause(Exception):
    """Raised when an Approval node pauses workflow execution pending human review."""

    def __init__(self, approval_id, token):
        self.approval_id = approval_id
        self.token = token
        super().__init__(f"Workflow paused for approval (id={approval_id}, token={token})")


class WorkflowApprovalRequest(models.Model):
    """
    Persists a pending human-approval request created by an Approval node.

    Each record represents one paused workflow execution waiting for a human
    to approve, reject, or expire. The unique ``token`` field is the only
    data exposed in the external approval URL, keeping record IDs private.

    States
    ------
    pending   - Awaiting a human decision.
    approved  - Approved; resumed execution on the Approved branch.
    rejected  - Rejected; resumed execution on the Rejected branch.
    expired   - Timeout elapsed; resumed execution on the Timeout branch.
    cancelled - Manually cancelled before a decision was made.
    """

    _name = 'workflow.approval.request'
    _description = 'Workflow Approval Request'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # Identity
    display_name = fields.Char(
        string='Reference',
        compute='_compute_display_name',
        store=True,
    )
    workflow_id = fields.Many2one(
        'work.auto',
        string='Workflow',
        ondelete='cascade',
        required=True,
        index=True,
    )
    node_id = fields.Many2one(
        'node.struct',
        string='Approval Node',
        ondelete='set null',
    )
    execution_id = fields.Char(
        string='Execution ID',
        index=True,
        help='Unique identifier for the paused execution context.',
    )

    # Secure token (Phase 3)
    token = fields.Char(
        string='Approval Token',
        required=True,
        copy=False,
        index=True,
        default=lambda self: str(uuid.uuid4()),
        help='Single-use UUID4 token embedded in the approval URL.',
    )
    token_used = fields.Boolean(
        string='Token Used',
        default=False,
        copy=False,
        help='Set to True once the token has been consumed to prevent replay attacks.',
    )

    # Approver
    approver_id = fields.Many2one(
        'res.users',
        string='Requested Approver',
        ondelete='set null',
    )
    approver_email = fields.Char(string='Approver Email')
    approver_name = fields.Char(string='Approver Name')

    # State
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending',
        required=True,
        string='State',
        index=True,
        tracking=True,
    )

    # Execution context — serialised Python dict persisted as JSON
    execution_context = fields.Json(
        string='Execution Context',
        copy=False,
        help='Serialised workflow execution context needed to resume the workflow.',
    )

    # Timing
    expiration = fields.Datetime(
        string='Expires At',
        help='If set, the approval request expires at this datetime.',
    )
    responded_at = fields.Datetime(string='Responded At')

    # Response
    response_comment = fields.Text(string='Comment')
    approver_ip = fields.Char(string='Approver IP')

    # Record reference (for audit / display)
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')

    # Reminder/escalation tracking
    reminder_count = fields.Integer(string='Reminders Sent', default=0)
    escalated = fields.Boolean(string='Escalated', default=False)

    # Timestamps
    create_date = fields.Datetime(string='Requested At', readonly=True)

    # Audit log
    log_ids = fields.One2many(
        'workflow.approval.log',
        'request_id',
        string='Audit Log',
        readonly=True,
    )

    @api.depends('workflow_id', 'state', 'token')
    def _compute_display_name(self):
        for rec in self:
            wf_name = rec.workflow_id.name or 'Unknown Workflow'
            rec.display_name = f"[{rec.state.upper()}] {wf_name} – {rec.token[:8]}…"

    # ------------------------------------------------------------------
    # Token helpers (Phase 3)
    # ------------------------------------------------------------------

    @api.model
    def get_by_token(self, token):
        """Return the approval request matching ``token``, or an empty recordset."""
        return self.sudo().search([('token', '=', token)], limit=1)

    def consume_token(self):
        """Mark the token as used. Raises if already consumed."""
        self.ensure_one()
        if self.token_used:
            raise exceptions.UserError(
                _("This approval link has already been used and is no longer valid.")
            )
        self.sudo().write({'token_used': True})

    def is_expired(self):
        """Return True if the request has passed its expiration datetime."""
        self.ensure_one()
        if not self.expiration:
            return False
        return fields.Datetime.now() >= self.expiration

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def action_approve(self, comment=None, approver_ip=None):
        """Mark request as approved and resume workflow on the Approved branch."""
        self.ensure_one()
        self._do_respond('approved', comment=comment, approver_ip=approver_ip)
        self._resume_workflow('approved')
        self._log_event('approved', comment=comment)

    def action_reject(self, comment=None, approver_ip=None):
        """Mark request as rejected and resume workflow on the Rejected branch."""
        self.ensure_one()
        self._do_respond('rejected', comment=comment, approver_ip=approver_ip)
        self._resume_workflow('rejected')
        self._log_event('rejected', comment=comment)

    def action_expire(self):
        """Called by the cron job when expiration datetime has passed."""
        self.ensure_one()
        if self.state != 'pending':
            return
        self.sudo().write({'state': 'expired', 'responded_at': fields.Datetime.now()})
        self._resume_workflow('timeout')
        self._log_event('expired')

    def action_cancel(self, comment=None):
        """Manually cancel a pending approval request."""
        self.ensure_one()
        if self.state != 'pending':
            raise exceptions.UserError(_("Only pending approval requests can be cancelled."))
        self.sudo().write({'state': 'cancelled', 'responded_at': fields.Datetime.now()})
        self._log_event('cancelled', comment=comment)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_respond(self, state, comment=None, approver_ip=None):
        self.sudo().write({
            'state': state,
            'responded_at': fields.Datetime.now(),
            'response_comment': comment or False,
            'approver_ip': approver_ip or False,
        })

    def _resume_workflow(self, branch):
        """
        Reconstruct and resume the paused workflow from the persisted context.

        ``branch`` is one of 'approved', 'rejected', 'timeout'.
        The branch name is injected into the execution context so the generated
        Approval node code can route to the correct output port.
        """
        self.ensure_one()
        if not self.execution_context:
            _logger.warning(
                "Approval request %d has no execution context — cannot resume workflow.",
                self.id,
            )
            return

        ctx = dict(self.execution_context)
        ctx['approval_branch'] = branch
        ctx['approval_status'] = self.state
        ctx['approval_comment'] = self.response_comment or ''
        ctx['approval_request_id'] = self.id
        ctx['approval_approver'] = self.approver_name or (
            self.approver_id.name if self.approver_id else ''
        )
        ctx['approval_responded_at'] = str(self.responded_at or '')
        ctx['approval_requested_at'] = str(self.create_date or '')

        workflow = self.workflow_id
        if not workflow or not workflow.active:
            _logger.warning(
                "Approval request %d: workflow '%s' is missing or inactive — skipping resume.",
                self.id,
                workflow.name if workflow else 'N/A',
            )
            return

        # Restore the record that was being processed.
        res_model = ctx.get('res_model') or self.res_model
        res_id = ctx.get('res_id') or self.res_id
        records = False
        if res_model and res_id:
            try:
                records = self.env[res_model].browse(res_id)
                if not records.exists():
                    records = False
            except Exception:
                records = False

        try:
            workflow._process({
                **ctx,
                'records': records,
                'current_record': records[:1] if records else False,
                '__approval_resume__': True,
            })
        except Exception as exc:
            _logger.error(
                "Failed to resume workflow '%s' (approval %d, branch=%s): %s",
                workflow.name, self.id, branch, exc,
            )

    def _log_event(self, event, comment=None):
        """Create an audit log entry."""
        self.env['workflow.approval.log'].sudo().create({
            'request_id': self.id,
            'event': event,
            'user_id': self.env.uid,
            'comment': comment or False,
        })


class WorkflowApprovalLog(models.Model):
    """
    Immutable audit log for every state change on a WorkflowApprovalRequest.

    Events: created, notified, reminded, escalated, approved, rejected,
            expired, cancelled, resumed.
    """

    _name = 'workflow.approval.log'
    _description = 'Workflow Approval Audit Log'
    _order = 'create_date asc'

    request_id = fields.Many2one(
        'workflow.approval.request',
        string='Approval Request',
        ondelete='cascade',
        required=True,
        index=True,
    )
    event = fields.Selection(
        selection=[
            ('created', 'Created'),
            ('notified', 'Notified'),
            ('reminded', 'Reminded'),
            ('escalated', 'Escalated'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
            ('resumed', 'Resumed'),
        ],
        required=True,
        string='Event',
    )
    user_id = fields.Many2one('res.users', string='By User', ondelete='set null')
    comment = fields.Text(string='Comment')
    create_date = fields.Datetime(string='Timestamp', readonly=True)
