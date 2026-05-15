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
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _get_active_record(self):
        """Return active record(s) from context if available."""
        active_model = self._context.get("active_model")
        active_ids = self._context.get("active_ids", [])
        if active_model and active_ids:
            return self.env[active_model].browse(active_ids)
        return None

    def _get_server_rules(self):
        """Fetch approval rules for this server action."""
        return self.env["approval.rule"].sudo().search([
            ("rule_type", "=", "server"),
            ("server_action_id", "=", self.id)
        ])

    def _parse_rule_domain(self, rule):
        """Parse domain text into Python list safely."""
        if not rule.domain:
            return []
        try:
            return safe_eval(rule.domain)
        except Exception:
            raise UserError(_(
                "Invalid domain in approval rule '%s': %s"
            ) % (rule.name, rule.domain))

    def _get_matched_rules(self, rules, active_record):
        """Return only the rules where domain is satisfied."""
        matched = []
        for rule in rules:
            domain = self._parse_rule_domain(rule)
            if not domain:
                matched.append(rule)
                continue
            if active_record and active_record.filtered_domain(domain):
                matched.append(rule)
        return matched

    def _check_existing_approval(self, rule, active_model, active_ids):
        """Check existing approval requests and block or allow execution."""
        ApprovalRequest = self.env["approval.request"].sudo()

        # Pending request → block execution
        pending = ApprovalRequest.search([
            ("rule_id", "=", rule.id),
            ("res_model", "=", active_model),
            ("res_id", "in", active_ids),
            ("state", "=", "pending"),
        ], limit=1)

        if pending:
            raise UserError(_(
                "This server action requires approval and is still pending.\n"
                "Rule: %s" % rule.name
            ))

        # Previously approved → allow execution
        approved = ApprovalRequest.search([
            ("rule_id", "=", rule.id),
            ("res_model", "=", active_model),
            ("res_id", "in", active_ids),
            ("state", "=", "approved"),
        ], limit=1)

        if approved:
            return "approved"

        return "no_request"

    def _open_approval_wizard(self, rule, active_model, res_id):
        """Return the approval wizard action for UI."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rule_id': rule.id,
                'default_res_model': active_model,
                'default_res_id': res_id,
            },
        }

    # ---------------------------------------------------------
    # Main Override
    # ---------------------------------------------------------

    @api.model
    def run(self):
        """
        Override: apply approval rules before server action executes.
        """
        # Fetch context-based data
        active_record = self._get_active_record()
        active_model = self._context.get("active_model")
        active_ids = self._context.get("active_ids", [])

        # Fetch rules for this action
        rules = self._get_server_rules()
        if not rules:
            return super(IrActionsServer, self).run()

        # Filter rules by domain
        matched_rules = self._get_matched_rules(rules, active_record)
        if not matched_rules:
            return super(IrActionsServer, self).run()

        # Process rules sequentially
        for rule in matched_rules:
            status = self._check_existing_approval(rule, active_model, active_ids)

            if status == "approved":
                continue  # allow, check next rule

            # No approval request yet → open wizard
            if status == "no_request":
                return self._open_approval_wizard(rule, active_model, active_ids[0])

        # All matched rules approved → execute server action
        return super(IrActionsServer, self).run()
